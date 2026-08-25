"""M2 authenticated task-center and Temporal workflow control APIs."""

from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status

from nexweave_api.errors import ApiProblem
from nexweave_api.m1_routes import (
    PROBLEM_RESPONSE,
    IdempotencyKey,
    IfMatch,
    PageCursor,
    PageLimit,
    PrincipalDependency,
    _paginate,
    _trace_id,
    _version_from_etag,
)
from nexweave_api.workflow_gateway import TemporalWorkflowGateway
from nexweave_api.workflow_repository import WorkflowRepository
from nexweave_contracts import (
    WorkflowCommandRequest,
    WorkflowCommandResponse,
    WorkflowReconcileResponse,
    WorkflowTaskCreate,
    WorkflowTaskDetailResponse,
    WorkflowTaskListResponse,
    WorkflowTaskResponse,
)
from nexweave_domain import (
    ROLE_ACTIONS,
    WORKFLOW_TEMPORAL_NAME,
    Role,
    WorkflowCommand,
    WorkflowRuleViolation,
    WorkflowTaskStatus,
    WorkflowType,
    available_workflow_commands,
    validate_workflow_command,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["workflow-tasks"],
    responses={
        400: PROBLEM_RESPONSE,
        401: PROBLEM_RESPONSE,
        403: PROBLEM_RESPONSE,
        404: PROBLEM_RESPONSE,
        409: PROBLEM_RESPONSE,
        412: PROBLEM_RESPONSE,
        422: PROBLEM_RESPONSE,
        503: PROBLEM_RESPONSE,
    },
)
WorkflowTypeFilter = Annotated[WorkflowType | None, Query()]
WorkflowStatusFilter = Annotated[WorkflowTaskStatus | None, Query(alias="status")]


def _repository(request: Request) -> WorkflowRepository:
    return cast(WorkflowRepository, request.app.state.repository)


def _gateway(request: Request) -> TemporalWorkflowGateway:
    return cast(TemporalWorkflowGateway, request.app.state.workflow_gateway)


@router.post(
    "/spaces/{space_id}/workflow-tasks",
    response_model=WorkflowTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_workflow_task(
    request: Request,
    response: Response,
    space_id: UUID,
    body: WorkflowTaskCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> WorkflowTaskResponse:
    repository = _repository(request)
    trace_id = _trace_id(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="workflow.create", trace_id=trace_id
    )
    task = await repository.create_workflow_task(
        principal=principal,
        space_id=space_id,
        payload=body.model_dump(mode="json"),
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    execution = await _gateway(request).start(
        workflow_name=WORKFLOW_TEMPORAL_NAME[body.workflow_type],
        workflow_id=str(task["workflow_id"]),
        payload=_start_payload(task, principal.actor_id, trace_id, body.start_paused),
    )
    task = await repository.mark_workflow_started(
        task_id=UUID(str(task["id"])),
        run_id=execution.run_id,
        actor_id=principal.actor_id,
        trace_id=trace_id,
    )
    response.headers["ETag"] = f'"v{task["version"]}"'
    response.headers["Location"] = f"/api/v1/workflow-tasks/{task['id']}"
    return WorkflowTaskResponse.model_validate(task)


@router.get(
    "/spaces/{space_id}/workflow-tasks",
    response_model=WorkflowTaskListResponse,
)
async def list_workflow_tasks(
    request: Request,
    space_id: UUID,
    principal: PrincipalDependency,
    response: Response,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
    workflow_type: WorkflowTypeFilter = None,
    task_status: WorkflowStatusFilter = None,
) -> WorkflowTaskListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="workflow.read",
        trace_id=_trace_id(request),
    )
    tasks = await repository.list_workflow_tasks(
        principal=principal,
        space_id=space_id,
        workflow_type=workflow_type,
        status=task_status,
    )
    response.headers["X-Projection-Source"] = "postgresql-read-model"
    return WorkflowTaskListResponse.model_validate(_paginate(tasks, limit, cursor))


@router.get("/workflow-tasks/{task_id}", response_model=WorkflowTaskDetailResponse)
async def get_workflow_task(
    request: Request,
    response: Response,
    task_id: UUID,
    principal: PrincipalDependency,
) -> WorkflowTaskDetailResponse:
    repository = _repository(request)
    detail = await repository.get_workflow_task_detail(task_id)
    task = detail["task"]
    facts = await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(task["space_id"])),
        action="workflow.read",
        trace_id=_trace_id(request),
    )
    response.headers["ETag"] = f'"v{task["version"]}"'
    response.headers["X-Projection-Source"] = "postgresql-read-model"
    return WorkflowTaskDetailResponse.model_validate(
        {
            **detail,
            "allowed_actions": _authorized_actions(
                available_workflow_commands(
                    WorkflowType(task["workflow_type"]), WorkflowTaskStatus(task["status"])
                ),
                principal.tenant_roles | facts.member_roles,
            ),
        }
    )


@router.post(
    "/workflow-tasks/{task_id}/commands",
    response_model=WorkflowCommandResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def command_workflow_task(
    request: Request,
    response: Response,
    task_id: UUID,
    body: WorkflowCommandRequest,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    if_match: IfMatch,
) -> WorkflowCommandResponse:
    repository = _repository(request)
    trace_id = _trace_id(request)
    expected_version = _version_from_etag(if_match)
    task = await repository.get_workflow_task(task_id)
    action = (
        "workflow.review"
        if body.action
        in {
            WorkflowCommand.CLAIM,
            WorkflowCommand.REQUEST_INPUT,
            WorkflowCommand.PROVIDE_INPUT,
            WorkflowCommand.APPROVE,
            WorkflowCommand.REJECT,
        }
        else "workflow.control"
    )
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(task["space_id"])),
        action=action,
        trace_id=trace_id,
    )
    cached = await repository.get_workflow_command_result(
        principal=principal,
        task_id=task_id,
        command=body.action,
        reason=body.reason,
        expected_version=expected_version,
        idempotency_key=idempotency_key,
    )
    if cached is not None:
        response.headers["ETag"] = f'"v{cached["task"]["version"]}"'
        return WorkflowCommandResponse.model_validate(
            {
                "task": cached["task"],
                "command_id": cached["command_id"],
                "duplicate": cached["duplicate"],
            }
        )
    task = await repository.assert_workflow_version(task_id, expected_version)
    try:
        validate_workflow_command(
            WorkflowType(task["workflow_type"]), WorkflowTaskStatus(task["status"]), body.action
        )
    except WorkflowRuleViolation as exc:
        raise ApiProblem(
            409,
            "WORKFLOW_COMMAND_REJECTED",
            "Workflow command rejected",
            str(exc),
        ) from exc

    if body.action is WorkflowCommand.RETRY:
        execution = await _gateway(request).retry(
            workflow_name=WORKFLOW_TEMPORAL_NAME[WorkflowType(task["workflow_type"])],
            workflow_id=str(task["workflow_id"]),
            payload=await repository.workflow_retry_payload(task_id, trace_id),
        )
        await repository.mark_workflow_started(
            task_id=task_id,
            run_id=execution.run_id,
            actor_id=principal.actor_id,
            trace_id=trace_id,
            restarted=True,
        )
        duplicate = False
    else:
        command_result = await _gateway(request).command(
            workflow_id=str(task["workflow_id"]),
            command_id=idempotency_key,
            action=body.action.value,
            reason=body.reason,
            actor_id=str(principal.actor_id),
        )
        duplicate = bool(command_result.get("duplicate", False))
    record = await repository.record_workflow_command(
        principal=principal,
        task_id=task_id,
        command=body.action,
        reason=body.reason,
        expected_version=expected_version,
        idempotency_key=idempotency_key,
        trace_id=trace_id,
        duplicate=duplicate,
    )
    response.headers["ETag"] = f'"v{record["task"]["version"]}"'
    return WorkflowCommandResponse.model_validate(
        {
            "task": record["task"],
            "command_id": record["command_id"],
            "duplicate": record["duplicate"],
        }
    )


@router.post(
    "/workflow-tasks/{task_id}/reconcile",
    response_model=WorkflowReconcileResponse,
)
async def reconcile_workflow_task(
    request: Request,
    task_id: UUID,
    principal: PrincipalDependency,
) -> WorkflowReconcileResponse:
    repository = _repository(request)
    task = await repository.get_workflow_task(task_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(task["space_id"])),
        action="workflow.reconcile",
        trace_id=_trace_id(request),
    )
    state = await _gateway(request).inspect(workflow_id=str(task["workflow_id"]))
    repaired_task, repaired = await repository.reconcile_workflow_task(
        principal=principal,
        task_id=task_id,
        temporal_state=state,
        trace_id=_trace_id(request),
    )
    return WorkflowReconcileResponse.model_validate(
        {
            "task": repaired_task,
            "repaired": repaired,
            "temporal_status": state.get("temporal_status", state["status"]),
        }
    )


def _start_payload(
    task: dict[str, object], actor_id: UUID, trace_id: str, start_paused: bool
) -> dict[str, object]:
    return {
        "task_id": task["id"],
        "tenant_id": task["tenant_id"],
        "space_id": task["space_id"],
        "workflow_type": task["workflow_type"],
        "workflow_id": task["workflow_id"],
        "input_refs": task["input_refs"],
        "start_paused": start_paused,
        "actor_id": str(actor_id),
        "trace_id": trace_id,
    }


def _authorized_actions(
    actions: tuple[WorkflowCommand, ...], roles: frozenset[Role]
) -> tuple[WorkflowCommand, ...]:
    allowed_capabilities = frozenset().union(*(ROLE_ACTIONS[role] for role in roles))
    return tuple(
        action
        for action in actions
        if (
            "workflow.review" in allowed_capabilities
            if action
            in {
                WorkflowCommand.CLAIM,
                WorkflowCommand.REQUEST_INPUT,
                WorkflowCommand.PROVIDE_INPUT,
                WorkflowCommand.APPROVE,
                WorkflowCommand.REJECT,
            }
            else "workflow.control" in allowed_capabilities
        )
    )
