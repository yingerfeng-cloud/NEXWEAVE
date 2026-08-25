from datetime import datetime
from typing import Any

from pydantic import UUID7, Field

from nexweave_contracts.base import ContractModel
from nexweave_domain import (
    ConnectorDefinitionStatus,
    DataClassification,
    GovernanceStatus,
)


class ModelProfileCreate(ContractModel):
    space_id: UUID7 | None = None
    name: str = Field(min_length=1, max_length=255)
    provider: str = Field(min_length=1, max_length=128)
    model_name: str = Field(min_length=1, max_length=255)
    credential_ref: str | None = Field(default=None, max_length=512)
    externally_hosted: bool = False
    maximum_classification: DataClassification = DataClassification.INTERNAL
    config: dict[str, Any] = Field(default_factory=dict)


class ModelProfileResponse(ModelProfileCreate):
    id: UUID7
    tenant_id: UUID7
    status: GovernanceStatus
    version: int = Field(ge=1)
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class ModelProfileListResponse(ContractModel):
    items: tuple[ModelProfileResponse, ...]
    next_cursor: str | None = None


class PromptVersionCreate(ContractModel):
    space_id: UUID7 | None = None
    prompt_key: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=50000)
    output_contract: dict[str, Any] = Field(default_factory=dict)


class PromptVersionResponse(PromptVersionCreate):
    id: UUID7
    tenant_id: UUID7
    revision: int = Field(ge=1)
    checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: GovernanceStatus
    created_at: datetime
    created_by: UUID7


class PromptVersionListResponse(ContractModel):
    items: tuple[PromptVersionResponse, ...]
    next_cursor: str | None = None


class ConnectorDefinitionCreate(ContractModel):
    space_id: UUID7 | None = None
    name: str = Field(min_length=1, max_length=255)
    connector_type: str = Field(min_length=1, max_length=128)
    config_schema: dict[str, Any] = Field(default_factory=dict)


class ConnectorDefinitionResponse(ConnectorDefinitionCreate):
    id: UUID7
    tenant_id: UUID7
    status: ConnectorDefinitionStatus
    version: int = Field(ge=1)
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class ConnectorDefinitionListResponse(ContractModel):
    items: tuple[ConnectorDefinitionResponse, ...]
    next_cursor: str | None = None


class AuditLogResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7 | None = None
    occurred_at: datetime
    actor_type: str
    actor_id: UUID7
    action: str
    resource_type: str
    resource_id: UUID7 | None = None
    trace_id: str | None = None
    outcome: str
    metadata: dict[str, Any]


class AuditLogListResponse(ContractModel):
    items: tuple[AuditLogResponse, ...]
    next_cursor: str | None = None
