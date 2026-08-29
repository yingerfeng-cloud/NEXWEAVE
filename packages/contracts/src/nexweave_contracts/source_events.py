"""Versioned M3 Source/Parse event data; Raw content is intentionally absent."""

from typing import Literal

from pydantic import UUID7, Field

from nexweave_contracts.base import ContractModel
from nexweave_domain import DataClassification, ParseJobStatus


class SourceEventContext(ContractModel):
    tenant_id: UUID7
    space_id: UUID7
    source_id: UUID7
    source_version_id: UUID7
    aggregate_version: int = Field(ge=1)
    correlation_id: UUID7
    causation_id: UUID7 | None = None
    trace_id: str = Field(pattern=r"^[0-9a-f]{32}$")


class SourceVersionReadyEventData(SourceEventContext):
    status: Literal["STORED"]
    checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    classification: DataClassification
    parse_job_id: UUID7
    workflow_id: str = Field(min_length=1, max_length=768)
    run_id: str | None = Field(default=None, max_length=255)


class SourceVersionSupersededEventData(SourceEventContext):
    old_source_version_id: UUID7
    new_source_version_id: UUID7
    reason: Literal["explicit-replacement"]


class SourceInvalidatedEventData(SourceEventContext):
    status: str = Field(min_length=1, max_length=32)
    reason_code: str = Field(min_length=1, max_length=128)
    policy_version: str = Field(min_length=1, max_length=128)


class ParseEventData(SourceEventContext):
    parse_job_id: UUID7
    status: Literal["SUCCEEDED", "PARTIAL_FAILED", "FAILED", "CANCELED"]
    parser_id: str = Field(min_length=1, max_length=128)
    parser_version: str = Field(min_length=1, max_length=64)
    config_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    document_model_version: str = Field(min_length=1, max_length=64)
    locator_version: str = Field(min_length=1, max_length=64)
    result_checksum: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    failure_count: int = Field(ge=0)
    error_code: str | None = Field(default=None, max_length=128)
    workflow_id: str = Field(min_length=1, max_length=768)
    run_id: str = Field(min_length=1, max_length=255)

    @property
    def terminal_status(self) -> ParseJobStatus:
        return ParseJobStatus(self.status)


# Compatibility name retained for existing generated-client imports.
SourceVersionEventData = SourceVersionReadyEventData
