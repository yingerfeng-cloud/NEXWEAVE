from datetime import datetime
from typing import Any

from pydantic import UUID7, Field, field_validator

from nexweave_contracts.base import ContractModel
from nexweave_domain import (
    WorkflowCommand,
    WorkflowStepStatus,
    WorkflowTaskStatus,
    WorkflowType,
)


class WorkflowTaskCreate(ContractModel):
    workflow_type: WorkflowType
    business_key: str = Field(
        min_length=1, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"
    )
    display_name: str = Field(min_length=1, max_length=255)
    input_refs: dict[str, str] = Field(default_factory=dict)
    start_paused: bool = False

    @field_validator("input_refs")
    @classmethod
    def input_refs_are_bounded_references(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 32:
            raise ValueError("input_refs cannot contain more than 32 references")
        if any(not key or len(key) > 128 or len(item) > 512 for key, item in value.items()):
            raise ValueError("input_refs keys and values exceed the M2 reference boundary")
        return value


class WorkflowTaskResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    workflow_type: WorkflowType
    business_key: str
    display_name: str
    workflow_id: str
    temporal_run_id: str | None = None
    status: WorkflowTaskStatus
    version: int = Field(ge=1)
    progress: int = Field(ge=0, le=100)
    current_step: str | None = None
    input_refs: dict[str, str]
    result_summary: dict[str, Any]
    error_code: str | None = None
    error_detail: str | None = None
    projection_revision: int = Field(ge=0)
    projection_in_sync: bool
    last_reconciled_at: datetime | None = None
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class WorkflowTaskListResponse(ContractModel):
    items: tuple[WorkflowTaskResponse, ...]
    next_cursor: str | None = None


class WorkflowStepResponse(ContractModel):
    id: UUID7
    task_id: UUID7
    step_key: str
    sequence: int = Field(ge=0)
    status: WorkflowStepStatus
    attempt: int = Field(ge=0)
    message: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime


class WorkflowEventResponse(ContractModel):
    id: UUID7
    task_id: UUID7
    event_key: str
    event_type: str
    workflow_status: WorkflowTaskStatus
    step_key: str | None = None
    message: str
    details: dict[str, Any]
    occurred_at: datetime


class WorkflowTaskDetailResponse(ContractModel):
    task: WorkflowTaskResponse
    steps: tuple[WorkflowStepResponse, ...]
    events: tuple[WorkflowEventResponse, ...]
    allowed_actions: tuple[WorkflowCommand, ...]


class WorkflowCommandRequest(ContractModel):
    action: WorkflowCommand
    reason: str = Field(default="", max_length=2000)


class WorkflowCommandResponse(ContractModel):
    task: WorkflowTaskResponse
    command_id: str
    duplicate: bool = False


class WorkflowReconcileResponse(ContractModel):
    task: WorkflowTaskResponse
    repaired: bool
    temporal_status: str


class WorkflowTaskEventData(ContractModel):
    task_id: UUID7
    workflow_id: str
    workflow_type: WorkflowType
    status: WorkflowTaskStatus
    change: str
    run_id: str | None = None
    projection_revision: int = Field(ge=0)
