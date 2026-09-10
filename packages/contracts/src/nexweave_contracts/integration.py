"""M8 Connector and Obsidian exchange public contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import UUID7, Field, field_validator, model_validator

from nexweave_contracts.base import ContractModel
from nexweave_domain import DataClassification

ConnectorKind = Literal["FILESYSTEM", "S3", "WEB_REST", "GIT"]
ConnectorStatus = Literal["DRAFT", "ACTIVE", "PAUSED", "FAILED", "REVOKED"]
SyncRunStatus = Literal["CREATED", "RUNNING", "PARTIAL_FAILED", "FAILED", "SUCCEEDED", "CANCELED"]
ObsidianImportStatus = Literal["DRAFT_CREATED", "CONFLICT"]


class ConnectorInstanceCreate(ContractModel):
    definition_id: UUID7
    name: str = Field(min_length=1, max_length=255)
    kind: ConnectorKind
    credential_ref: str | None = Field(default=None, max_length=512)
    allowlist: tuple[str, ...] = Field(min_length=1, max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)
    field_mapping: dict[str, str] = Field(default_factory=dict)
    classification: DataClassification = DataClassification.INTERNAL

    @field_validator("allowlist")
    @classmethod
    def normalized_allowlist(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item or len(item) > 1024 for item in normalized):
            raise ValueError("allowlist entries must be non-empty bounded targets")
        if len(set(normalized)) != len(normalized):
            raise ValueError("allowlist entries must be unique")
        return normalized

    @model_validator(mode="after")
    def reject_inline_secrets(self) -> ConnectorInstanceCreate:
        forbidden = {"secret", "password", "token", "api_key", "access_key", "private_key"}
        if any(key.casefold() in forbidden for key in self.config):
            raise ValueError("connector config may not contain inline credentials")
        return self


class ConnectorInstanceResponse(ConnectorInstanceCreate):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    status: ConnectorStatus
    config_checksum: str
    watermark: dict[str, Any]
    version: int = Field(ge=1)
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class ConnectorInstanceListResponse(ContractModel):
    items: tuple[ConnectorInstanceResponse, ...]


class ConnectorSyncRunCreate(ContractModel):
    requested_watermark: dict[str, Any] = Field(default_factory=dict)


class ConnectorSyncRunResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    connector_instance_id: UUID7
    workflow_task_id: UUID7
    workflow_id: str
    temporal_run_id: str | None = None
    status: SyncRunStatus
    requested_watermark: dict[str, Any]
    resulting_watermark: dict[str, Any]
    result_summary: dict[str, Any]
    error_code: str | None = None
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class ObsidianExportResponse(ContractModel):
    export_id: UUID7
    wiki_page_id: UUID7
    wiki_page_version_id: UUID7
    content_checksum: str
    markdown: str


class ObsidianImportCreate(ContractModel):
    markdown: str = Field(min_length=1, max_length=2_000_000)


class ObsidianImportResponse(ContractModel):
    id: UUID7
    status: ObsidianImportStatus
    wiki_page_id: UUID7 | None = None
    base_version_id: UUID7 | None = None
    draft_version_id: UUID7 | None = None
    conflict_id: UUID7 | None = None
    markdown_diff: str
