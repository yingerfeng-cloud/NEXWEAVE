"""Authenticated M7 quality, Release, graph and trusted-query APIs."""
# ruff: noqa: E501

from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import AwareDatetime

from nexweave_api.m1_routes import (
    IdempotencyKey,
    IfMatch,
    PrincipalDependency,
    _trace_id,
    _version_from_etag,
)
from nexweave_api.release_repository import ReleaseRepository
from nexweave_api.workflow_gateway import TemporalWorkflowGateway
from nexweave_contracts import (
    EvaluationRunCreate,
    EvaluationRunResponse,
    EvaluationSuiteCreate,
    EvaluationSuiteResponse,
    GraphTraverseResponse,
    QueryAnswerResponse,
    QueryCreate,
    ReleaseCandidateCreate,
    ReleaseCandidateListResponse,
    ReleaseCandidateResponse,
    ReleaseDeprecationCreate,
    ReleaseListResponse,
    ReleasePointerResponse,
    ReleasePointerSwitch,
    ReleasePublish,
    ReleaseResponse,
)
from nexweave_domain import WorkflowType

router = APIRouter(prefix="/api/v1", tags=["quality", "releases", "graph", "query"])


def _repository(request: Request) -> ReleaseRepository:
    return cast(ReleaseRepository, request.app.state.repository)


def _gateway(request: Request) -> TemporalWorkflowGateway:
    return cast(TemporalWorkflowGateway, request.app.state.workflow_gateway)


@router.post(
    "/spaces/{space_id}/evaluation-suites",
    response_model=EvaluationSuiteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_suite(
    request: Request,
    space_id: UUID,
    body: EvaluationSuiteCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> EvaluationSuiteResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="quality.manage", trace_id=_trace_id(request)
    )
    return EvaluationSuiteResponse.model_validate(
        await repository.create_evaluation_suite(
            principal=principal,
            space_id=space_id,
            payload=body.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.get("/spaces/{space_id}/evaluation-suites", response_model=list[EvaluationSuiteResponse])
async def list_suites(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> list[EvaluationSuiteResponse]:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="quality.read", trace_id=_trace_id(request)
    )
    return [
        EvaluationSuiteResponse.model_validate(item)
        for item in await repository.list_evaluation_suites(principal=principal, space_id=space_id)
    ]


@router.post(
    "/spaces/{space_id}/evaluations/runs",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_evaluation(
    request: Request,
    space_id: UUID,
    body: EvaluationRunCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> EvaluationRunResponse:
    repository, trace_id = _repository(request), _trace_id(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="quality.run", trace_id=trace_id
    )
    business_key = f"{body.target_type}:{body.target_id}:{body.suite_id}:{sha256(idempotency_key.encode()).hexdigest()[:16]}"
    task = await repository.create_workflow_task(
        principal=principal,
        space_id=space_id,
        payload={
            "workflow_type": WorkflowType.QUALITY_EVALUATION.value,
            "business_key": business_key,
            "display_name": "Fixed-target quality evaluation",
            "input_refs": {
                "target_type": body.target_type,
                "target_id": str(body.target_id),
                "suite_id": str(body.suite_id),
            },
            "start_paused": False,
        },
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    run = await repository.create_evaluation_run(
        principal=principal,
        space_id=space_id,
        payload=body.model_dump(mode="json"),
        workflow_task_id=UUID(str(task["id"])),
        workflow_id=str(task["workflow_id"]),
        trace_id=trace_id,
    )
    execution = await _gateway(request).start(
        workflow_name="nexweave.quality-evaluation.v2",
        workflow_id=str(task["workflow_id"]),
        payload={
            "workflow_type": WorkflowType.QUALITY_EVALUATION.value,
            "task_id": str(task["id"]),
            "evaluation_run_id": str(run["id"]),
            "actor_id": str(principal.actor_id),
            "trace_id": trace_id,
        },
    )
    await repository.mark_workflow_started(
        task_id=UUID(str(task["id"])),
        run_id=execution.run_id,
        actor_id=principal.actor_id,
        trace_id=trace_id,
    )
    return EvaluationRunResponse.model_validate(run)


@router.get("/evaluations/runs/{run_id}", response_model=EvaluationRunResponse)
async def get_evaluation(
    request: Request, run_id: UUID, principal: PrincipalDependency
) -> EvaluationRunResponse:
    repository = _repository(request)
    run = await repository.get_evaluation_run(principal=principal, run_id=run_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(run["space_id"])),
        action="quality.read",
        trace_id=_trace_id(request),
    )
    return EvaluationRunResponse.model_validate(run)


@router.post(
    "/spaces/{space_id}/release-candidates",
    response_model=ReleaseCandidateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_candidate(
    request: Request,
    space_id: UUID,
    body: ReleaseCandidateCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ReleaseCandidateResponse:
    repository, trace_id = _repository(request), _trace_id(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="release.create", trace_id=trace_id
    )
    business_key = f"{body.version}:{sha256(idempotency_key.encode()).hexdigest()[:16]}"
    task = await repository.create_workflow_task(
        principal=principal,
        space_id=space_id,
        payload={
            "workflow_type": WorkflowType.KNOWLEDGE_RELEASE.value,
            "business_key": business_key,
            "display_name": f"Publish immutable Release {body.version}",
            "input_refs": {
                "version": body.version,
                "schema_version_id": str(body.schema_version_id),
            },
            "start_paused": False,
        },
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    candidate = await repository.create_release_candidate(
        principal=principal,
        space_id=space_id,
        payload=body.model_dump(mode="json"),
        workflow_task_id=UUID(str(task["id"])),
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    execution = await _gateway(request).start(
        workflow_name="nexweave.knowledge-release.v2",
        workflow_id=str(task["workflow_id"]),
        payload={
            "workflow_type": WorkflowType.KNOWLEDGE_RELEASE.value,
            "task_id": str(task["id"]),
            "release_candidate_id": str(candidate["id"]),
            "actor_id": str(principal.actor_id),
            "trace_id": trace_id,
            "approval_timeout_seconds": 86400,
        },
    )
    await repository.mark_workflow_started(
        task_id=UUID(str(task["id"])),
        run_id=execution.run_id,
        actor_id=principal.actor_id,
        trace_id=trace_id,
    )
    return ReleaseCandidateResponse.model_validate(candidate)


@router.get("/spaces/{space_id}/release-candidates", response_model=ReleaseCandidateListResponse)
async def list_candidates(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> ReleaseCandidateListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="release.read", trace_id=_trace_id(request)
    )
    return ReleaseCandidateListResponse.model_validate(
        {"items": await repository.list_release_candidates(principal=principal, space_id=space_id)}
    )


@router.get("/release-candidates/{candidate_id}", response_model=ReleaseCandidateResponse)
async def get_candidate(
    request: Request, candidate_id: UUID, principal: PrincipalDependency
) -> ReleaseCandidateResponse:
    repository = _repository(request)
    candidate = await repository.get_release_candidate(
        principal=principal, candidate_id=candidate_id
    )
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(candidate["space_id"])),
        action="release.read",
        trace_id=_trace_id(request),
    )
    return ReleaseCandidateResponse.model_validate(candidate)


@router.post(
    "/release-candidates/{candidate_id}/publish",
    response_model=ReleaseCandidateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def publish_candidate(
    request: Request,
    candidate_id: UUID,
    body: ReleasePublish,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ReleaseCandidateResponse:
    repository, trace_id = _repository(request), _trace_id(request)
    candidate = await repository.get_release_candidate(
        principal=principal, candidate_id=candidate_id
    )
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(candidate["space_id"])),
        action="release.publish",
        trace_id=trace_id,
    )
    updated = await repository.record_release_approval(
        principal=principal,
        candidate_id=candidate_id,
        decision="APPROVED",
        reason=body.reason,
        channel=body.channel,
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    await _gateway(request).command(
        workflow_id=str(candidate["workflow_id"]),
        command_id=idempotency_key,
        action="APPROVE",
        reason=body.reason,
        actor_id=str(principal.actor_id),
    )
    return ReleaseCandidateResponse.model_validate({**candidate, **updated})


@router.get("/spaces/{space_id}/releases", response_model=ReleaseListResponse)
async def list_releases(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> ReleaseListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="release.read", trace_id=_trace_id(request)
    )
    return ReleaseListResponse.model_validate(
        {"items": await repository.list_releases(principal=principal, space_id=space_id)}
    )


@router.get("/releases/{release_id}", response_model=ReleaseResponse)
async def get_release(
    request: Request, release_id: UUID, principal: PrincipalDependency
) -> ReleaseResponse:
    repository = _repository(request)
    release = await repository.get_release(principal=principal, release_id=release_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(release["space_id"])),
        action="release.read",
        trace_id=_trace_id(request),
    )
    return ReleaseResponse.model_validate(release)


@router.get("/releases/{release_id}/export", response_class=Response)
async def export_release(
    request: Request,
    release_id: UUID,
    principal: PrincipalDependency,
    format: Literal["json", "markdown"] = "json",
) -> Response:
    repository = _repository(request)
    release = await repository.get_release(principal=principal, release_id=release_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(release["space_id"])),
        action="release.read",
        trace_id=_trace_id(request),
    )
    exported = await repository.export_release(principal=principal, release_id=release_id)
    if format == "json":
        return JSONResponse(exported)
    lines = [
        f"# NEXWEAVE Release {release['version']}",
        "",
        f"- Release ID: `{release_id}`",
        f"- Manifest checksum: `{release['manifest_checksum']}`",
        f"- Published at: `{release['published_at']}`",
        "",
        "## Immutable items",
        "",
    ]
    for item in exported["items"]:
        lines.extend(
            (
                f"### {item['object_type']} `{item['object_id']}`",
                "",
                f"Checksum: `{item.get('object_checksum') or 'n/a'}`",
                "",
                "```json",
                json.dumps(item["snapshot"], ensure_ascii=False, indent=2),
                "```",
                "",
            )
        )
    return PlainTextResponse("\n".join(lines), media_type="text/markdown; charset=utf-8")


@router.post("/releases/{release_id}/projections/rebuild")
async def rebuild_projection(
    request: Request,
    release_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> dict[str, object]:
    repository = _repository(request)
    release = await repository.get_release(principal=principal, release_id=release_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(release["space_id"])),
        action="release.publish",
        trace_id=_trace_id(request),
    )
    return await repository.rebuild_release_projection(
        principal=principal,
        release_id=release_id,
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )


@router.post("/spaces/{space_id}/release-pointer", response_model=ReleasePointerResponse)
async def switch_pointer(
    request: Request,
    space_id: UUID,
    body: ReleasePointerSwitch,
    principal: PrincipalDependency,
    if_match: IfMatch,
    idempotency_key: IdempotencyKey,
) -> ReleasePointerResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="release.switch", trace_id=_trace_id(request)
    )
    return ReleasePointerResponse.model_validate(
        await repository.switch_release_pointer(
            principal=principal,
            space_id=space_id,
            release_id=body.release_id,
            channel=body.channel,
            reason=body.reason,
            expected_version=_version_from_etag(if_match),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.get("/spaces/{space_id}/release-pointer", response_model=ReleasePointerResponse)
async def get_pointer(
    request: Request, space_id: UUID, principal: PrincipalDependency, channel: str = "stable"
) -> ReleasePointerResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="release.read", trace_id=_trace_id(request)
    )
    return ReleasePointerResponse.model_validate(
        await repository.get_release_pointer(
            principal=principal, space_id=space_id, channel=channel
        )
    )


@router.post("/releases/{release_id}/deprecations", response_model=ReleaseResponse)
async def deprecate_release(
    request: Request,
    release_id: UUID,
    body: ReleaseDeprecationCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ReleaseResponse:
    repository = _repository(request)
    release = await repository.get_release(principal=principal, release_id=release_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(release["space_id"])),
        action="release.deprecate",
        trace_id=_trace_id(request),
    )
    return ReleaseResponse.model_validate(
        await repository.deprecate_release(
            principal=principal,
            release_id=release_id,
            reason=body.reason,
            replacement_release_id=body.replacement_release_id,
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.post("/releases/{release_id}/queries", response_model=QueryAnswerResponse)
async def ask_release(
    request: Request, release_id: UUID, body: QueryCreate, principal: PrincipalDependency
) -> QueryAnswerResponse:
    repository = _repository(request)
    release = await repository.get_release(principal=principal, release_id=release_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(release["space_id"])),
        action="query.release",
        trace_id=_trace_id(request),
    )
    return QueryAnswerResponse.model_validate(
        await repository.query_release(
            principal=principal,
            release_id=release_id,
            payload=body.model_dump(mode="json"),
            trace_id=_trace_id(request),
        )
    )


@router.get("/query-answers/{answer_id}", response_model=QueryAnswerResponse)
async def get_answer(
    request: Request, answer_id: UUID, principal: PrincipalDependency
) -> QueryAnswerResponse:
    repository = _repository(request)
    answer = await repository.get_query_answer(principal=principal, answer_id=answer_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(answer["space_id"])),
        action="query.answer.read",
        trace_id=_trace_id(request),
    )
    return QueryAnswerResponse.model_validate(answer)


@router.get("/releases/{release_id}/graph/traverse", response_model=GraphTraverseResponse)
async def graph_traverse(
    request: Request,
    release_id: UUID,
    principal: PrincipalDependency,
    start_entity_id: UUID,
    target_entity_id: UUID | None = None,
    mode: Literal["TRAVERSE", "SHORTEST", "CAUSAL"] = "TRAVERSE",
    max_depth: int = Query(default=1, ge=1, le=5),
    causal_only: bool = False,
    as_of: AwareDatetime | None = None,
) -> GraphTraverseResponse:
    repository = _repository(request)
    release = await repository.get_release(principal=principal, release_id=release_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(release["space_id"])),
        action="graph.read",
        trace_id=_trace_id(request),
    )
    return GraphTraverseResponse.model_validate(
        await repository.traverse_graph(
            principal=principal,
            release_id=release_id,
            start_entity_id=start_entity_id,
            target_entity_id=target_entity_id,
            mode=mode,
            max_depth=max_depth,
            causal_only=causal_only,
            as_of=as_of,
        )
    )
