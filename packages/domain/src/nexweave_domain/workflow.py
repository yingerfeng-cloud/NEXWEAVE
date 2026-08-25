"""M2 reliable-workflow task vocabulary and transition policy."""

from __future__ import annotations

from enum import StrEnum


class WorkflowType(StrEnum):
    SOURCE_INGESTION = "SOURCE_INGESTION"
    KNOWLEDGE_COMPILE = "KNOWLEDGE_COMPILE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    QUALITY_EVALUATION = "QUALITY_EVALUATION"
    KNOWLEDGE_RELEASE = "KNOWLEDGE_RELEASE"
    DOMAIN_PACK_INSTALL = "DOMAIN_PACK_INSTALL"
    GRIDCREW_FEEDBACK_INGESTION = "GRIDCREW_FEEDBACK_INGESTION"


class WorkflowTaskStatus(StrEnum):
    CREATED = "CREATED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WAITING = "WAITING"
    WAITING_INPUT = "WAITING_INPUT"
    CANCELLING = "CANCELLING"
    COMPENSATING = "COMPENSATING"
    CANCELLED = "CANCELLED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    REJECTED = "REJECTED"


class WorkflowStepStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    PAUSED = "PAUSED"
    WAITING = "WAITING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    COMPENSATED = "COMPENSATED"


class WorkflowCommand(StrEnum):
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    CANCEL = "CANCEL"
    CLAIM = "CLAIM"
    REQUEST_INPUT = "REQUEST_INPUT"
    PROVIDE_INPUT = "PROVIDE_INPUT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    RETRY = "RETRY"


WORKFLOW_ID_PREFIX: dict[WorkflowType, str] = {
    WorkflowType.SOURCE_INGESTION: "source-ingestion",
    WorkflowType.KNOWLEDGE_COMPILE: "compile",
    WorkflowType.HUMAN_REVIEW: "review",
    WorkflowType.QUALITY_EVALUATION: "evaluation",
    WorkflowType.KNOWLEDGE_RELEASE: "release",
    WorkflowType.DOMAIN_PACK_INSTALL: "pack-install",
    WorkflowType.GRIDCREW_FEEDBACK_INGESTION: "gridcrew-feedback",
}

WORKFLOW_TEMPORAL_NAME: dict[WorkflowType, str] = {
    WorkflowType.SOURCE_INGESTION: "nexweave.source-ingestion.v1",
    WorkflowType.KNOWLEDGE_COMPILE: "nexweave.knowledge-compile.v1",
    WorkflowType.HUMAN_REVIEW: "nexweave.human-review.v1",
    WorkflowType.QUALITY_EVALUATION: "nexweave.quality-evaluation.v1",
    WorkflowType.KNOWLEDGE_RELEASE: "nexweave.knowledge-release.v1",
    WorkflowType.DOMAIN_PACK_INSTALL: "nexweave.domain-pack-install.v1",
    WorkflowType.GRIDCREW_FEEDBACK_INGESTION: "nexweave.gridcrew-feedback-ingestion.v1",
}

WORKFLOW_STEP_PLAN: dict[WorkflowType, tuple[str, ...]] = {
    WorkflowType.SOURCE_INGESTION: (
        "validate-upload-reference",
        "retryable-scan-boundary-stub",
        "prepare-parse-handoff-stub",
    ),
    WorkflowType.KNOWLEDGE_COMPILE: (
        "lock-version-references",
        "retryable-compile-step-graph-stub",
        "persist-candidate-summary-stub",
    ),
    WorkflowType.HUMAN_REVIEW: (
        "materialize-review-projection",
        "wait-for-human-decision",
        "persist-review-decision-stub",
    ),
    WorkflowType.QUALITY_EVALUATION: (
        "materialize-fixed-target-stub",
        "retryable-evaluation-stub",
        "aggregate-gate-summary-stub",
    ),
    WorkflowType.KNOWLEDGE_RELEASE: (
        "validate-release-boundaries-stub",
        "wait-for-release-approval",
        "freeze-and-project-stub",
    ),
    WorkflowType.DOMAIN_PACK_INSTALL: (
        "verify-declarative-pack-boundary-stub",
        "wait-for-install-approval",
        "apply-declarations-stub",
    ),
    WorkflowType.GRIDCREW_FEEDBACK_INGESTION: (
        "validate-integration-boundary-stub",
        "retryable-deduplicate-feedback-stub",
        "create-controlled-intake-summary-stub",
    ),
}

APPROVAL_WORKFLOW_TYPES = frozenset(
    {
        WorkflowType.HUMAN_REVIEW,
        WorkflowType.KNOWLEDGE_RELEASE,
        WorkflowType.DOMAIN_PACK_INSTALL,
    }
)

TERMINAL_WORKFLOW_STATUSES = frozenset(
    {
        WorkflowTaskStatus.CANCELLED,
        WorkflowTaskStatus.SUCCEEDED,
        WorkflowTaskStatus.FAILED,
        WorkflowTaskStatus.TIMED_OUT,
        WorkflowTaskStatus.REJECTED,
    }
)


class WorkflowRuleViolation(ValueError):
    """Raised when a workflow command violates the public state policy."""


def stable_workflow_id(workflow_type: WorkflowType, tenant_id: object, business_key: str) -> str:
    """Derive the frozen Temporal Workflow ID from a stable business key."""

    return f"{WORKFLOW_ID_PREFIX[workflow_type]}/{tenant_id}/{business_key}"


def available_workflow_commands(
    workflow_type: WorkflowType, status: WorkflowTaskStatus
) -> tuple[WorkflowCommand, ...]:
    if status is WorkflowTaskStatus.RUNNING:
        return (WorkflowCommand.PAUSE, WorkflowCommand.CANCEL)
    if status is WorkflowTaskStatus.PAUSED:
        return (WorkflowCommand.RESUME, WorkflowCommand.CANCEL)
    if status is WorkflowTaskStatus.WAITING_INPUT:
        return (WorkflowCommand.PROVIDE_INPUT, WorkflowCommand.CANCEL)
    if status is WorkflowTaskStatus.WAITING:
        if workflow_type is WorkflowType.HUMAN_REVIEW:
            return (
                WorkflowCommand.CLAIM,
                WorkflowCommand.REQUEST_INPUT,
                WorkflowCommand.APPROVE,
                WorkflowCommand.REJECT,
                WorkflowCommand.CANCEL,
            )
        if workflow_type in {
            WorkflowType.KNOWLEDGE_RELEASE,
            WorkflowType.DOMAIN_PACK_INSTALL,
        }:
            return (
                WorkflowCommand.APPROVE,
                WorkflowCommand.REJECT,
                WorkflowCommand.CANCEL,
            )
        return (WorkflowCommand.CANCEL,)
    if status in {WorkflowTaskStatus.FAILED, WorkflowTaskStatus.TIMED_OUT}:
        return (WorkflowCommand.RETRY,)
    return ()


def validate_workflow_command(
    workflow_type: WorkflowType, status: WorkflowTaskStatus, command: WorkflowCommand
) -> None:
    if command not in available_workflow_commands(workflow_type, status):
        raise WorkflowRuleViolation(
            f"{command.value} is not allowed for {workflow_type.value} in {status.value}"
        )
