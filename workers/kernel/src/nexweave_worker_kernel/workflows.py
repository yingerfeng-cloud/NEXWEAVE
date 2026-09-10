"""Deterministic Temporal definitions for the seven M2 workflow types."""
# ruff: noqa: E501

from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from nexweave_domain import (
        APPROVAL_WORKFLOW_TYPES,
        WORKFLOW_STEP_PLAN,
        WorkflowCommand,
        WorkflowTaskStatus,
        WorkflowType,
        available_workflow_commands,
    )

ACTIVITY_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=5),
    maximum_attempts=3,
    non_retryable_error_types=["M2_KERNEL_POLICY_VIOLATION"],
)

SOURCE_ACTIVITY_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=15),
    maximum_attempts=3,
    non_retryable_error_types=[
        "SOURCE_CHECKSUM_MISMATCH",
        "SOURCE_MALWARE_DETECTED",
        "SOURCE_MALWARE_SCAN_FAILED",
        "SOURCE_SECURITY_POLICY_FAILED",
        "SOURCE_TYPE_UNSUPPORTED",
        "PARSER_CAPABILITY_UNAVAILABLE",
        "PARSER_RESOURCE_LIMIT_EXCEEDED",
        "PARSE_RESULT_INVALID",
    ],
)


class _KernelWorkflow:
    def __init__(self) -> None:
        self._payload: dict[str, Any] = {}
        self._workflow_type = WorkflowType.SOURCE_INGESTION
        self._status = WorkflowTaskStatus.CREATED
        self._progress = 0
        self._current_step: str | None = None
        self._cancel_requested = False
        self._approval_decision: str | None = None
        self._approval_escalated = False
        self._processed_commands: dict[str, dict[str, Any]] = {}
        self._completed_steps: list[str] = []
        self._event_sequence = 0

    async def _run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._payload = payload
        self._workflow_type = WorkflowType(payload["workflow_type"])
        self._status = (
            WorkflowTaskStatus.PAUSED
            if bool(payload.get("start_paused"))
            else WorkflowTaskStatus.RUNNING
        )
        await self._project("RUN_STARTED", message="Temporal run started")
        if self._status is WorkflowTaskStatus.PAUSED:
            await self._wait_while_paused()

        steps = WORKFLOW_STEP_PLAN[self._workflow_type]
        try:
            for index, step_key in enumerate(steps, start=1):
                self._current_step = step_key
                if self._cancel_requested:
                    return await self._compensate_and_cancel()
                await self._wait_while_paused()
                if self._cancel_requested:
                    return await self._compensate_and_cancel()
                if self._workflow_type in APPROVAL_WORKFLOW_TYPES and "wait-for-" in step_key:
                    gate_result = await self._wait_for_approval(step_key)
                    if gate_result is not None:
                        return gate_result

                self._status = WorkflowTaskStatus.RUNNING
                await self._project(
                    "STEP_STARTED",
                    step_key=step_key,
                    step_status="RUNNING",
                    message=f"Kernel step {index}/{len(steps)} started",
                )
                execution = await workflow.execute_activity(
                    "execute_m2_kernel_step",
                    {"task_id": payload["task_id"], "step_key": step_key},
                    task_queue=payload["activity_task_queue"],
                    start_to_close_timeout=timedelta(seconds=15),
                    schedule_to_close_timeout=timedelta(seconds=45),
                    heartbeat_timeout=timedelta(seconds=5),
                    retry_policy=ACTIVITY_RETRY_POLICY,
                )
                self._completed_steps.append(step_key)
                self._progress = int(index * 100 / len(steps))
                await self._project(
                    "STEP_SUCCEEDED",
                    step_key=step_key,
                    step_status="SUCCEEDED",
                    attempt=int(execution["attempt"]),
                    message="M2 kernel boundary stub completed",
                    details={"kernel_outcome": "STUB_SUCCEEDED"},
                )
            self._status = WorkflowTaskStatus.SUCCEEDED
            self._current_step = None
            result = {
                "kernel_outcome": "STUB_SUCCEEDED",
                "workflow_type": self._workflow_type.value,
                "business_features_implemented": False,
            }
            await self._project(
                "RUN_SUCCEEDED",
                progress=100,
                message="M2 workflow kernel run succeeded",
                result_summary=result,
            )
            return result
        except ActivityError as exc:
            self._status = WorkflowTaskStatus.FAILED
            await self._project(
                "RUN_FAILED",
                step_key=self._current_step,
                step_status="FAILED" if self._current_step else None,
                message="Retry policy exhausted",
                error_code="ACTIVITY_RETRY_EXHAUSTED",
                error_detail=type(exc).__name__,
            )
            raise

    async def _wait_while_paused(self) -> None:
        if self._status is not WorkflowTaskStatus.PAUSED:
            return
        await workflow.wait_condition(
            lambda: self._status is not WorkflowTaskStatus.PAUSED or self._cancel_requested
        )

    async def _wait_for_approval(self, step_key: str) -> dict[str, Any] | None:
        self._status = WorkflowTaskStatus.WAITING
        await self._project(
            "APPROVAL_WAITING",
            step_key=step_key,
            step_status="WAITING",
            message="Waiting for an authorized human decision",
        )
        try:
            await workflow.wait_condition(
                lambda: self._approval_decision is not None or self._cancel_requested,
                timeout=timedelta(seconds=int(self._payload.get("approval_timeout_seconds", 300))),
            )
        except TimeoutError:
            self._approval_escalated = True
            await self._project(
                "APPROVAL_TIMEOUT_ESCALATED",
                step_key=step_key,
                step_status="WAITING",
                message="Human decision timeout escalated; decision remains required",
            )
            await workflow.wait_condition(
                lambda: self._approval_decision is not None or self._cancel_requested
            )
        if self._cancel_requested:
            await workflow.wait_condition(lambda: workflow.all_handlers_finished())
            return await self._compensate_and_cancel()
        if self._approval_decision == "REJECTED":
            self._status = WorkflowTaskStatus.REJECTED
            await self._project(
                "RUN_REJECTED",
                step_key=step_key,
                step_status="FAILED",
                message="Authorized human rejected the workflow",
            )
            return {"kernel_outcome": "REJECTED", "workflow_type": self._workflow_type.value}
        self._status = WorkflowTaskStatus.RUNNING
        return None

    async def _compensate_and_cancel(self) -> dict[str, Any]:
        self._status = WorkflowTaskStatus.COMPENSATING
        await self._project("COMPENSATION_STARTED", message="Compensation started")
        for step_key in reversed(self._completed_steps):
            await workflow.execute_activity(
                "compensate_m2_kernel_step",
                {"task_id": self._payload["task_id"], "step_key": step_key},
                task_queue=self._payload["activity_task_queue"],
                start_to_close_timeout=timedelta(seconds=15),
                heartbeat_timeout=timedelta(seconds=5),
                retry_policy=ACTIVITY_RETRY_POLICY,
            )
            await self._project(
                "STEP_COMPENSATED",
                step_key=step_key,
                step_status="COMPENSATED",
                message="M2 kernel step compensated",
            )
        self._status = WorkflowTaskStatus.CANCELLED
        self._current_step = None
        await self._project("RUN_CANCELLED", message="Workflow cancelled after compensation")
        return {"kernel_outcome": "CANCELLED", "workflow_type": self._workflow_type.value}

    async def _handle_command(self, command: dict[str, Any], *, project: bool) -> dict[str, Any]:
        command_id = str(command["command_id"])
        if command_id in self._processed_commands:
            return {**self._processed_commands[command_id], "duplicate": True}
        action = WorkflowCommand(command["action"])
        if action not in available_workflow_commands(self._workflow_type, self._status):
            raise ApplicationError(
                f"{action.value} is not allowed while {self._status.value}",
                type="M2_KERNEL_POLICY_VIOLATION",
                non_retryable=True,
            )

        if action is WorkflowCommand.PAUSE:
            self._status = WorkflowTaskStatus.PAUSED
        elif action is WorkflowCommand.RESUME:
            self._status = WorkflowTaskStatus.RUNNING
        elif action is WorkflowCommand.CANCEL:
            self._cancel_requested = True
            self._status = WorkflowTaskStatus.CANCELLING
        elif action is WorkflowCommand.REQUEST_INPUT:
            self._status = WorkflowTaskStatus.WAITING_INPUT
        elif action is WorkflowCommand.PROVIDE_INPUT:
            self._status = WorkflowTaskStatus.WAITING
        elif action is WorkflowCommand.APPROVE:
            self._approval_decision = "APPROVED"
            self._status = WorkflowTaskStatus.RUNNING
        elif action is WorkflowCommand.REJECT:
            self._approval_decision = "REJECTED"
            self._status = WorkflowTaskStatus.REJECTED

        result = {
            "command_id": command_id,
            "action": action.value,
            "status": self._status.value,
            "duplicate": False,
            "run_id": workflow.info().run_id,
        }
        self._processed_commands[command_id] = result
        if project:
            await self._project(
                f"COMMAND_{action.value}",
                message=str(command.get("reason") or f"{action.value} accepted"),
                actor_id=str(command["actor_id"]),
                details={"command_id": command_id},
            )
        return result

    async def _project(
        self,
        event_type: str,
        *,
        step_key: str | None = None,
        step_status: str | None = None,
        attempt: int = 0,
        progress: int | None = None,
        message: str,
        actor_id: str | None = None,
        details: dict[str, Any] | None = None,
        result_summary: dict[str, Any] | None = None,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        self._event_sequence += 1
        event_key = f"run:{workflow.info().run_id}:event:{self._event_sequence}:{event_type}"
        payload = {
            "task_id": self._payload["task_id"],
            "actor_id": actor_id or self._payload["actor_id"],
            "trace_id": self._payload["trace_id"],
            "run_id": workflow.info().run_id,
            "event_key": event_key,
            "event_type": event_type,
            "status": self._status.value,
            "step_key": step_key,
            "step_status": step_status,
            "attempt": attempt,
            "progress": self._progress if progress is None else progress,
            "message": message,
            "details": details or {},
            "result_summary": result_summary or {},
            "error_code": error_code,
            "error_detail": error_detail,
        }
        await workflow.execute_activity(
            "record_projection_transition",
            payload,
            task_queue=self._payload["activity_task_queue"],
            start_to_close_timeout=timedelta(seconds=15),
            schedule_to_close_timeout=timedelta(seconds=45),
            heartbeat_timeout=timedelta(seconds=5),
            retry_policy=ACTIVITY_RETRY_POLICY,
        )

    def _state(self) -> dict[str, Any]:
        return {
            "workflow_id": workflow.info().workflow_id,
            "run_id": workflow.info().run_id,
            "workflow_type": self._workflow_type.value,
            "status": self._status.value,
            "progress": self._progress,
            "current_step": self._current_step,
            "cancel_requested": self._cancel_requested,
            "approval_decision": self._approval_decision,
            "approval_escalated": self._approval_escalated,
            "completed_steps": list(self._completed_steps),
            "projection_revision": self._event_sequence,
        }


@workflow.defn(name="nexweave.source-ingestion.v1")
class SourceIngestionWorkflow(_KernelWorkflow):
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._run(payload)

    @workflow.update(name="command")
    async def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._handle_command(payload, project=True)

    @workflow.signal(name="notify")
    async def notify(self, payload: dict[str, Any]) -> None:
        await self._handle_command(payload, project=False)

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


@workflow.defn(name="nexweave.source-ingestion.v2")
class SourceIngestionV2Workflow:
    """M3 business workflow; it carries references only and performs no direct I/O."""

    def __init__(self) -> None:
        self._status = "CREATED"
        self._current_step: str | None = None
        self._parse_job_id = ""

    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._parse_job_id = str(payload["parse_job_id"])
        activity_queue = str(payload["activity_task_queue"])
        run_id = workflow.info().run_id
        self._status = "RUNNING"
        try:
            self._current_step = "load-and-verify-raw"
            await workflow.execute_activity(
                "m3_source_verify_raw",
                {"parse_job_id": self._parse_job_id, "run_id": run_id},
                task_queue=activity_queue,
                start_to_close_timeout=timedelta(seconds=45),
                schedule_to_close_timeout=timedelta(minutes=3),
                heartbeat_timeout=timedelta(seconds=10),
                retry_policy=SOURCE_ACTIVITY_RETRY_POLICY,
            )
            self._current_step = "malware-security-scan"
            await workflow.execute_activity(
                "m3_source_scan_raw",
                {"parse_job_id": self._parse_job_id, "run_id": run_id},
                task_queue=activity_queue,
                start_to_close_timeout=timedelta(minutes=3),
                schedule_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(seconds=10),
                retry_policy=SOURCE_ACTIVITY_RETRY_POLICY,
            )
            self._current_step = "parse-validate-persist-relocate-finalize"
            result = await workflow.execute_activity(
                "m3_source_parse_and_persist",
                {"parse_job_id": self._parse_job_id, "run_id": run_id},
                task_queue=activity_queue,
                start_to_close_timeout=timedelta(minutes=10),
                schedule_to_close_timeout=timedelta(minutes=30),
                heartbeat_timeout=timedelta(seconds=10),
                retry_policy=SOURCE_ACTIVITY_RETRY_POLICY,
            )
            self._status = str(result["status"])
            self._current_step = None
            return dict(result)
        except ActivityError as exc:
            cause = exc.cause
            code = (
                cause.type
                if isinstance(cause, ApplicationError) and cause.type
                else "SOURCE_PARSE_ACTIVITY_FAILED"
            )
            detail = type(cause).__name__ if cause is not None else type(exc).__name__
            self._status = "FAILED"
            await workflow.execute_activity(
                "m3_source_fail",
                {
                    "parse_job_id": self._parse_job_id,
                    "run_id": run_id,
                    "code": code,
                    "detail": detail,
                },
                task_queue=activity_queue,
                start_to_close_timeout=timedelta(seconds=30),
                schedule_to_close_timeout=timedelta(minutes=3),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
            raise

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return {
            "workflow_id": workflow.info().workflow_id,
            "run_id": workflow.info().run_id,
            "workflow_type": "SOURCE_INGESTION_V2",
            "parse_job_id": self._parse_job_id,
            "status": self._status,
            "current_step": self._current_step,
        }


@workflow.defn(name="nexweave.knowledge-compile.v1")
class KnowledgeCompileWorkflow(_KernelWorkflow):
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._run(payload)

    @workflow.update(name="command")
    async def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._handle_command(payload, project=True)

    @workflow.signal(name="notify")
    async def notify(self, payload: dict[str, Any]) -> None:
        await self._handle_command(payload, project=False)

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


@workflow.defn(name="nexweave.knowledge-compile.v2")
class KnowledgeCompileV2Workflow(_KernelWorkflow):
    """M5 Compile orchestration; all model and database I/O stays in Activities."""

    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._payload = payload
        self._workflow_type = WorkflowType.KNOWLEDGE_COMPILE
        self._status = WorkflowTaskStatus.RUNNING
        self._current_step = "structured-extract"
        await self._project("RUN_STARTED", message="Governed knowledge compilation started")
        await self._project(
            "STEP_STARTED",
            step_key=self._current_step,
            step_status="RUNNING",
            progress=20,
            message="Fixed Source/Schema/Prompt/Model inputs are being compiled",
        )
        try:
            result = await workflow.execute_activity(
                "m5_compile_execute",
                {
                    "compile_job_id": payload["compile_job_id"],
                    "run_id": workflow.info().run_id,
                    "trace_id": payload["trace_id"],
                },
                task_queue=payload["activity_task_queue"],
                start_to_close_timeout=timedelta(minutes=10),
                schedule_to_close_timeout=timedelta(minutes=30),
                heartbeat_timeout=timedelta(seconds=15),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    non_retryable_error_types=[
                        "COMPILE_SCHEMA_NOT_PUBLISHED",
                        "COMPILE_SOURCE_NOT_READY",
                        "MODEL_CLASSIFICATION_DENIED",
                        "MODEL_EGRESS_DENIED",
                        "MODEL_BUDGET_EXCEEDED",
                    ],
                ),
            )
            self._completed_steps.append(self._current_step)
            self._progress = 100
            self._status = WorkflowTaskStatus.SUCCEEDED
            await self._project(
                "STEP_SUCCEEDED",
                step_key=self._current_step,
                step_status="SUCCEEDED",
                progress=100,
                message="Candidate knowledge and Wiki drafts persisted",
                details={"stats": result.get("stats", {})},
            )
            self._current_step = None
            await self._project(
                "RUN_SUCCEEDED",
                progress=100,
                message="Knowledge compilation succeeded; outputs remain drafts",
                result_summary=result,
            )
            return dict(result)
        except ActivityError as exc:
            cause = exc.cause
            code = (
                cause.type
                if isinstance(cause, ApplicationError) and cause.type
                else "COMPILE_ACTIVITY_FAILED"
            )
            self._status = WorkflowTaskStatus.FAILED
            await workflow.execute_activity(
                "m5_compile_fail",
                {
                    "compile_job_id": payload["compile_job_id"],
                    "code": code,
                    "detail": type(cause).__name__ if cause is not None else type(exc).__name__,
                    "trace_id": payload["trace_id"],
                },
                task_queue=payload["activity_task_queue"],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
            await self._project(
                "RUN_FAILED",
                step_key=self._current_step,
                step_status="FAILED",
                message="Knowledge compilation failed safely",
                error_code=code,
                error_detail=type(cause).__name__ if cause is not None else type(exc).__name__,
            )
            raise

    @workflow.update(name="command")
    async def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._handle_command(payload, project=True)

    @workflow.signal(name="notify")
    async def notify(self, payload: dict[str, Any]) -> None:
        await self._handle_command(payload, project=False)

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


@workflow.defn(name="nexweave.human-review.v1")
class HumanReviewWorkflow(_KernelWorkflow):
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._run(payload)

    @workflow.update(name="command")
    async def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._handle_command(payload, project=True)

    @workflow.signal(name="notify")
    async def notify(self, payload: dict[str, Any]) -> None:
        await self._handle_command(payload, project=False)

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


@workflow.defn(name="nexweave.human-review.v2")
class HumanReviewV2Workflow(_KernelWorkflow):
    """M6 review lifecycle: materialize once, then wait for the audited final decision."""

    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._payload = payload
        self._workflow_type = WorkflowType.HUMAN_REVIEW
        self._status = WorkflowTaskStatus.RUNNING
        self._current_step = "materialize-review-case"
        await self._project(
            "RUN_STARTED",
            step_key=self._current_step,
            step_status="RUNNING",
            message="HumanReview v2 materialized its governed review case",
        )
        self._completed_steps.append(self._current_step)
        self._progress = 25
        await self._project(
            "STEP_SUCCEEDED",
            step_key=self._current_step,
            step_status="SUCCEEDED",
            progress=self._progress,
            message="Review tasks are persisted; awaiting audited human decisions",
        )
        self._current_step = "wait-for-audited-final-decision"
        self._status = WorkflowTaskStatus.WAITING
        await self._project(
            "APPROVAL_WAITING",
            step_key=self._current_step,
            step_status="WAITING",
            message="Waiting for the final approved or rejected review action",
        )
        try:
            await workflow.wait_condition(
                lambda: self._approval_decision is not None or self._cancel_requested,
                timeout=timedelta(seconds=int(payload.get("approval_timeout_seconds", 300))),
            )
        except TimeoutError:
            self._approval_escalated = True
            await self._project(
                "APPROVAL_TIMEOUT_ESCALATED",
                step_key=self._current_step,
                step_status="WAITING",
                message="Review decision timeout escalated; final decision remains required",
            )
            await workflow.wait_condition(
                lambda: self._approval_decision is not None or self._cancel_requested
            )
        if self._cancel_requested:
            await workflow.wait_condition(lambda: workflow.all_handlers_finished())
            return await self._compensate_and_cancel()
        if self._approval_decision == "REJECTED":
            self._status = WorkflowTaskStatus.REJECTED
            await self._project(
                "RUN_REJECTED",
                step_key=self._current_step,
                step_status="FAILED",
                message="Final governed review decision rejected the target",
            )
            await workflow.wait_condition(lambda: workflow.all_handlers_finished())
            return {"review_case_id": payload["review_case_id"], "status": "REJECTED"}
        self._status = WorkflowTaskStatus.SUCCEEDED
        self._progress = 100
        await self._project(
            "RUN_SUCCEEDED",
            step_key=self._current_step,
            step_status="SUCCEEDED",
            progress=100,
            message="Final governed review decision recorded",
            result_summary={"review_case_id": payload["review_case_id"], "status": "APPROVED"},
        )
        await workflow.wait_condition(lambda: workflow.all_handlers_finished())
        return {"review_case_id": payload["review_case_id"], "status": "APPROVED"}

    @workflow.update(name="command")
    async def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._handle_command(payload, project=True)

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


@workflow.defn(name="nexweave.quality-evaluation.v1")
class QualityEvaluationWorkflow(_KernelWorkflow):
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._run(payload)

    @workflow.update(name="command")
    async def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._handle_command(payload, project=True)

    @workflow.signal(name="notify")
    async def notify(self, payload: dict[str, Any]) -> None:
        await self._handle_command(payload, project=False)

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


@workflow.defn(name="nexweave.quality-evaluation.v2")
class QualityEvaluationV2Workflow(_KernelWorkflow):
    """M7 fixed-target evaluation; all query/database work stays in one idempotent Activity."""

    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._payload = payload
        self._workflow_type = WorkflowType.QUALITY_EVALUATION
        self._status = WorkflowTaskStatus.RUNNING
        self._current_step = "evaluate-fixed-target"
        await self._project("RUN_STARTED", message="Fixed-target quality evaluation started")
        try:
            result = await workflow.execute_activity(
                "m7_quality_evaluate",
                {"evaluation_run_id": payload["evaluation_run_id"]},
                task_queue=payload["activity_task_queue"],
                start_to_close_timeout=timedelta(minutes=10),
                schedule_to_close_timeout=timedelta(minutes=30),
                heartbeat_timeout=timedelta(seconds=15),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            self._status = WorkflowTaskStatus.SUCCEEDED
            self._progress = 100
            self._current_step = None
            await self._project(
                "RUN_SUCCEEDED",
                progress=100,
                message="Evaluation results and question-level errors persisted",
                result_summary=result,
            )
            return dict(result)
        except ActivityError:
            self._status = WorkflowTaskStatus.FAILED
            await self._project(
                "RUN_FAILED",
                step_key=self._current_step,
                step_status="FAILED",
                message="Quality evaluation failed safely",
                error_code="EVALUATION_ACTIVITY_FAILED",
            )
            raise

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


@workflow.defn(name="nexweave.knowledge-release.v1")
class KnowledgeReleaseWorkflow(_KernelWorkflow):
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._run(payload)

    @workflow.update(name="command")
    async def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._handle_command(payload, project=True)

    @workflow.signal(name="notify")
    async def notify(self, payload: dict[str, Any]) -> None:
        await self._handle_command(payload, project=False)

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


@workflow.defn(name="nexweave.knowledge-release.v2")
class KnowledgeReleaseV2Workflow(_KernelWorkflow):
    """M7 validate, wait for an audited independent approval, then publish atomically."""

    def __init__(self) -> None:
        super().__init__()
        self._approval_actor_id: str | None = None

    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._payload = payload
        self._workflow_type = WorkflowType.KNOWLEDGE_RELEASE
        self._status = WorkflowTaskStatus.RUNNING
        self._current_step = "quality-and-release-gate"
        await self._project("RUN_STARTED", message="KnowledgeRelease v2 validation started")
        gate = await workflow.execute_activity(
            "m7_release_validate",
            {
                "release_candidate_id": payload["release_candidate_id"],
                "trace_id": payload["trace_id"],
            },
            task_queue=payload["activity_task_queue"],
            start_to_close_timeout=timedelta(minutes=10),
            schedule_to_close_timeout=timedelta(minutes=30),
            heartbeat_timeout=timedelta(seconds=15),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        if gate.get("error_code"):
            self._status = WorkflowTaskStatus.FAILED
            await self._project(
                "RUN_FAILED",
                step_key=self._current_step,
                step_status="FAILED",
                message="Release quality gate rejected the candidate",
                error_code=str(gate["error_code"]),
                result_summary=gate,
            )
            return {"status": "FAILED", "gate": gate}
        self._progress = 50
        self._status = WorkflowTaskStatus.WAITING
        self._current_step = "wait-for-independent-publisher"
        await self._project(
            "APPROVAL_WAITING",
            step_key=self._current_step,
            step_status="WAITING",
            progress=50,
            message="Quality gate passed; waiting for an audited independent Publisher",
            details={"gate": gate},
        )
        try:
            await workflow.wait_condition(
                lambda: self._approval_decision is not None,
                timeout=timedelta(seconds=int(payload.get("approval_timeout_seconds", 86400))),
            )
        except TimeoutError:
            self._approval_escalated = True
            await self._project(
                "APPROVAL_TIMEOUT_ESCALATED",
                step_key=self._current_step,
                step_status="WAITING",
                message="Release approval timed out; publication remains blocked",
            )
            await workflow.wait_condition(lambda: self._approval_decision is not None)
        if self._approval_decision == "REJECTED":
            self._status = WorkflowTaskStatus.REJECTED
            await self._project("RUN_REJECTED", message="Publisher rejected the ReleaseCandidate")
            await workflow.wait_condition(lambda: workflow.all_handlers_finished())
            return {"status": "REJECTED", "gate": gate}
        self._status = WorkflowTaskStatus.RUNNING
        self._current_step = "publish-immutable-release"
        result = await workflow.execute_activity(
            "m7_release_publish",
            {
                "release_candidate_id": payload["release_candidate_id"],
                "approver_id": self._approval_actor_id,
                "trace_id": payload["trace_id"],
            },
            task_queue=payload["activity_task_queue"],
            start_to_close_timeout=timedelta(minutes=10),
            schedule_to_close_timeout=timedelta(minutes=30),
            heartbeat_timeout=timedelta(seconds=15),
            retry_policy=RetryPolicy(maximum_attempts=5),
        )
        self._status = WorkflowTaskStatus.SUCCEEDED
        self._progress = 100
        self._current_step = None
        await self._project(
            "RUN_SUCCEEDED",
            progress=100,
            message="Immutable Release and rebuildable projections published",
            result_summary=result,
        )
        await workflow.wait_condition(lambda: workflow.all_handlers_finished())
        return dict(result)

    @workflow.update(name="command")
    async def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        command_id = str(payload["command_id"])
        if command_id in self._processed_commands:
            return {**self._processed_commands[command_id], "duplicate": True}
        action = str(payload["action"])
        if action not in {"APPROVE", "REJECT"} or self._status is not WorkflowTaskStatus.WAITING:
            raise ApplicationError(
                "Only approval or rejection is allowed while Release waits",
                type="RELEASE_WORKFLOW_POLICY_VIOLATION",
                non_retryable=True,
            )
        self._approval_decision = "APPROVED" if action == "APPROVE" else "REJECTED"
        self._approval_actor_id = str(payload["actor_id"])
        result = {
            "command_id": command_id,
            "action": action,
            "status": self._approval_decision,
            "duplicate": False,
            "run_id": workflow.info().run_id,
        }
        self._processed_commands[command_id] = result
        await self._project(
            f"COMMAND_{action}",
            message=str(payload.get("reason") or action),
            actor_id=self._approval_actor_id,
            details={"command_id": command_id},
        )
        return result

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return {**self._state(), "approval_actor_id": self._approval_actor_id}


@workflow.defn(name="nexweave.domain-pack-install.v1")
class DomainPackInstallWorkflow(_KernelWorkflow):
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._run(payload)

    @workflow.update(name="command")
    async def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._handle_command(payload, project=True)

    @workflow.signal(name="notify")
    async def notify(self, payload: dict[str, Any]) -> None:
        await self._handle_command(payload, project=False)

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


@workflow.defn(name="nexweave.domain-pack-install.v2")
class DomainPackInstallV2Workflow(_KernelWorkflow):
    """M4 Pack workflow: reference-only orchestration with all I/O in Activities."""

    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._payload = payload
        self._workflow_type = WorkflowType.DOMAIN_PACK_INSTALL
        self._status = WorkflowTaskStatus.RUNNING
        self._current_step = "resolve-compose-persist-candidate"
        await self._project("RUN_STARTED", message="Domain Pack installation started")
        await self._project(
            "STEP_STARTED",
            step_key=self._current_step,
            step_status="RUNNING",
            message="Resolving signed dependencies and composing candidate SchemaVersion",
        )
        try:
            result = await workflow.execute_activity(
                "m4_pack_resolve_compose_persist",
                {
                    "installation_id": payload["installation_id"],
                    "run_id": workflow.info().run_id,
                    "trace_id": payload["trace_id"],
                },
                task_queue=payload["activity_task_queue"],
                start_to_close_timeout=timedelta(minutes=5),
                schedule_to_close_timeout=timedelta(minutes=15),
                heartbeat_timeout=timedelta(seconds=15),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            self._completed_steps.append(self._current_step)
            self._progress = 100
            self._status = WorkflowTaskStatus.SUCCEEDED
            await self._project(
                "STEP_SUCCEEDED",
                step_key=self._current_step,
                step_status="SUCCEEDED",
                progress=100,
                message="Candidate SchemaVersion persisted; publication remains separate",
            )
            self._current_step = None
            summary = {
                "installation_id": payload["installation_id"],
                "candidate_schema_version_id": result.get("candidate_schema_version_id"),
                "status": result.get("status"),
            }
            await self._project(
                "RUN_SUCCEEDED",
                progress=100,
                message="Domain Pack installation workflow succeeded",
                result_summary=summary,
            )
            return summary
        except ActivityError as exc:
            cause = exc.cause
            code = (
                cause.type
                if isinstance(cause, ApplicationError) and cause.type
                else "PACK_INSTALLATION_FAILED"
            )
            self._status = WorkflowTaskStatus.FAILED
            await workflow.execute_activity(
                "m4_pack_fail",
                {
                    "installation_id": payload["installation_id"],
                    "actor_id": payload["actor_id"],
                    "code": code,
                    "trace_id": payload["trace_id"],
                },
                task_queue=payload["activity_task_queue"],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
            await self._project(
                "RUN_FAILED",
                step_key=self._current_step,
                step_status="FAILED",
                message="Domain Pack installation was rejected or failed",
                error_code=code,
                error_detail=type(cause).__name__ if cause is not None else type(exc).__name__,
            )
            raise

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


@workflow.defn(name="nexweave.gridcrew-feedback-ingestion.v1")
class GridCrewFeedbackIngestionWorkflow(_KernelWorkflow):
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._run(payload)

    @workflow.update(name="command")
    async def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._handle_command(payload, project=True)

    @workflow.signal(name="notify")
    async def notify(self, payload: dict[str, Any]) -> None:
        await self._handle_command(payload, project=False)

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


@workflow.defn(name="nexweave.connector-sync.v2")
class ConnectorSyncV2Workflow(_KernelWorkflow):
    """Read external bytes in an Activity, then reuse M3 SourceIngestion v2."""

    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._payload = payload
        self._workflow_type = WorkflowType.CONNECTOR_SYNC
        self._status = WorkflowTaskStatus.RUNNING
        self._current_step = "read-allowlisted-source"
        await self._project("RUN_STARTED", message="Read-only connector synchronization started")
        try:
            registered = await workflow.execute_activity(
                "m8_connector_read_register_raw",
                {
                    "connector_sync_run_id": payload["connector_sync_run_id"],
                    "trace_id": payload["trace_id"],
                },
                task_queue=payload["activity_task_queue"],
                start_to_close_timeout=timedelta(minutes=5),
                schedule_to_close_timeout=timedelta(minutes=15),
                heartbeat_timeout=timedelta(seconds=15),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    non_retryable_error_types=[
                        "CONNECTOR_ALLOWLIST_DENIED",
                        "CONNECTOR_RESOURCE_LIMIT_EXCEEDED",
                    ],
                ),
            )
            self._current_step = "start-source-parse"
            parsed = await workflow.execute_child_workflow(
                "nexweave.source-ingestion.v2",
                {
                    "parse_job_id": registered["parse_job_id"],
                    "trace_id": payload["trace_id"],
                    "activity_task_queue": payload["parser_activity_task_queue"],
                },
                id=registered["parse_workflow_id"],
                task_queue=payload["workflow_task_queue"],
            )
            await workflow.execute_activity(
                "m8_connector_complete",
                {
                    "connector_sync_run_id": payload["connector_sync_run_id"],
                    "watermark": registered["watermark"],
                    "source_version_id": registered["source_version_id"],
                    "parse_job_id": registered["parse_job_id"],
                },
                task_queue=payload["activity_task_queue"],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
            self._status, self._progress, self._current_step = (
                WorkflowTaskStatus.SUCCEEDED,
                100,
                None,
            )
            summary = {
                "connector_sync_run_id": payload["connector_sync_run_id"],
                "source_version_id": registered["source_version_id"],
                "parse_status": parsed.get("status"),
            }
            await self._project(
                "RUN_SUCCEEDED",
                progress=100,
                message="Raw SourceVersion and parse result persisted",
                result_summary=summary,
            )
            return summary
        except ActivityError as exc:
            self._status = WorkflowTaskStatus.FAILED
            await self._project(
                "RUN_FAILED",
                step_key=self._current_step,
                step_status="FAILED",
                message="Connector synchronization failed safely",
                error_code="CONNECTOR_SYNC_FAILED",
                error_detail=type(exc.cause).__name__
                if exc.cause is not None
                else type(exc).__name__,
            )
            raise

    @workflow.query(name="state")
    def state(self) -> dict[str, Any]:
        return self._state()


WORKFLOW_CLASSES = [
    SourceIngestionWorkflow,
    SourceIngestionV2Workflow,
    KnowledgeCompileWorkflow,
    KnowledgeCompileV2Workflow,
    HumanReviewWorkflow,
    HumanReviewV2Workflow,
    QualityEvaluationWorkflow,
    QualityEvaluationV2Workflow,
    KnowledgeReleaseWorkflow,
    KnowledgeReleaseV2Workflow,
    DomainPackInstallWorkflow,
    DomainPackInstallV2Workflow,
    GridCrewFeedbackIngestionWorkflow,
    ConnectorSyncV2Workflow,
]
