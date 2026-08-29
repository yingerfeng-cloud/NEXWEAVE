"""M3 public Source, parse and unified-document contracts."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from typing import Annotated, Literal

from pydantic import UUID7, Field, model_validator

from nexweave_contracts.base import ContractModel
from nexweave_contracts.source_anchor import Locator, SourceAnchor
from nexweave_domain import (
    BlockType,
    DataClassification,
    FailureScope,
    ImportBatchStatus,
    ParseJobStatus,
    SourceDocumentStatus,
    SourceUploadStatus,
    SourceVersionState,
)

Sha256 = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class ParserBudget(ContractModel):
    max_input_bytes: int = Field(default=104_857_600, ge=1, le=536_870_912)
    max_pages: int = Field(default=2_000, ge=1, le=20_000)
    max_sheets: int = Field(default=200, ge=1, le=5_000)
    max_rows: int = Field(default=100_000, ge=1, le=1_000_000)
    max_columns: int = Field(default=2_000, ge=1, le=16_384)
    max_segments: int = Field(default=200_000, ge=1, le=1_000_000)
    max_output_chars: int = Field(default=20_000_000, ge=1, le=200_000_000)
    timeout_seconds: int = Field(default=120, ge=1, le=3_600)


class ParserConfig(ContractModel):
    budget: ParserBudget = Field(default_factory=ParserBudget)


class ParserCapability(ContractModel):
    provider_id: str = Field(min_length=1, max_length=128)
    provider_version: str = Field(min_length=1, max_length=64)
    mime_types: tuple[str, ...] = Field(min_length=1)
    block_types: tuple[BlockType, ...] = Field(min_length=1)
    supports_scanned_pdf_detection: bool = False
    supports_ocr: bool = False


class ControlledObjectRef(ContractModel):
    source_version_id: UUID7
    object_key: str = Field(
        pattern=r"^raw/v1/[0-9a-f-]+/[0-9a-f-]+/[0-9a-f-]+/[0-9a-f-]+/[0-9a-f]{64}$"
    )
    object_version_id: str | None = Field(default=None, max_length=1024)
    checksum_sha256: Sha256
    content_type: str = Field(min_length=1, max_length=255)
    size: int = Field(ge=1)


class ParseRequest(ContractModel):
    parse_job_id: UUID7
    source: ControlledObjectRef
    filename: str = Field(min_length=1, max_length=512)
    parser_id: str = Field(min_length=1, max_length=128)
    parser_version: str = Field(min_length=1, max_length=64)
    config_checksum: Sha256
    document_model_version: Literal["1.0"] = "1.0"
    locator_version: Literal["1.0"] = "1.0"
    budget: ParserBudget = Field(default_factory=ParserBudget)


class SegmentLocator(ContractModel):
    locator: Locator


class DocumentSegment(ContractModel):
    id: UUID7
    source_version_id: UUID7
    parse_job_id: UUID7
    sequence: int = Field(ge=0)
    block_type: BlockType
    structure_path: str = Field(min_length=1, max_length=2048)
    normalized_text: str | None = Field(default=None, max_length=2_000_000)
    derived_object_key: str | None = Field(default=None, max_length=2048)
    text_checksum: Sha256
    page_number: int | None = Field(default=None, ge=1)
    sheet_name: str | None = Field(default=None, max_length=255)
    table_id: str | None = Field(default=None, max_length=512)
    row_index: int | None = Field(default=None, ge=0)
    column_index: int | None = Field(default=None, ge=0)
    locators: tuple[Locator, ...] = Field(min_length=1)
    parser_id: str = Field(min_length=1, max_length=128)
    parser_version: str = Field(min_length=1, max_length=64)
    config_checksum: Sha256
    document_model_version: Literal["1.0"] = "1.0"
    locator_version: Literal["1.0"] = "1.0"

    @model_validator(mode="after")
    def text_or_derived_reference_is_required(self) -> DocumentSegment:
        if self.normalized_text is None and self.derived_object_key is None:
            raise ValueError("a segment requires normalized text or a derived object reference")
        return self


class ParseFailureUnit(ContractModel):
    id: UUID7
    parse_job_id: UUID7
    error_code: str = Field(min_length=1, max_length=128)
    scope: FailureScope
    scope_ref: str = Field(min_length=1, max_length=512)
    retryable: bool
    safe_detail: str = Field(min_length=1, max_length=1024)


class ParseSecurityStats(ContractModel):
    input_bytes: int = Field(ge=0)
    page_count: int = Field(default=0, ge=0)
    sheet_count: int = Field(default=0, ge=0)
    zip_entry_count: int = Field(default=0, ge=0)
    expanded_bytes: int = Field(default=0, ge=0)
    external_relationships_blocked: int = Field(default=0, ge=0)
    embedded_objects_blocked: int = Field(default=0, ge=0)
    scanned_page_count: int = Field(default=0, ge=0)


class ParseResultManifest(ContractModel):
    parse_job_id: UUID7
    source_version_id: UUID7
    source_checksum: Sha256
    parser_id: str
    parser_version: str
    config_checksum: Sha256
    document_model_version: Literal["1.0"] = "1.0"
    locator_version: Literal["1.0"] = "1.0"
    status: ParseJobStatus
    segments: tuple[DocumentSegment, ...]
    anchors: tuple[SourceAnchor, ...]
    failure_units: tuple[ParseFailureUnit, ...] = ()
    security_stats: ParseSecurityStats
    result_checksum: Sha256

    @model_validator(mode="after")
    def terminal_status_matches_outputs(self) -> ParseResultManifest:
        if self.status is ParseJobStatus.SUCCEEDED and (
            not self.segments or not self.anchors or self.failure_units
        ):
            raise ValueError("successful parse requires segments and anchors without failures")
        if self.status is ParseJobStatus.PARTIAL_FAILED and not (
            self.segments and self.anchors and self.failure_units
        ):
            raise ValueError("partial parse requires usable segments, anchors and failure units")
        if self.status in {ParseJobStatus.FAILED, ParseJobStatus.CANCELED} and (
            self.segments or self.anchors
        ):
            raise ValueError("failed or canceled parse cannot expose usable output")
        if self.status not in {
            ParseJobStatus.SUCCEEDED,
            ParseJobStatus.PARTIAL_FAILED,
            ParseJobStatus.FAILED,
            ParseJobStatus.CANCELED,
        }:
            raise ValueError("a result manifest must be terminal")
        if len(self.segments) != len(self.anchors):
            raise ValueError("each usable segment requires exactly one SourceAnchor")
        if [segment.sequence for segment in self.segments] != list(range(len(self.segments))):
            raise ValueError("segment sequence must be contiguous and deterministic")
        if len({segment.id for segment in self.segments}) != len(self.segments):
            raise ValueError("segment identifiers must be unique")
        if len({anchor.id for anchor in self.anchors}) != len(self.anchors):
            raise ValueError("anchor identifiers must be unique")
        for segment in self.segments:
            if (
                segment.source_version_id != self.source_version_id
                or segment.parse_job_id != self.parse_job_id
                or segment.parser_id != self.parser_id
                or segment.parser_version != self.parser_version
                or segment.config_checksum != self.config_checksum
                or segment.document_model_version != self.document_model_version
                or segment.locator_version != self.locator_version
            ):
                raise ValueError("segment binding does not match the immutable ParseJob")
            if segment.normalized_text is not None and segment.text_checksum != _sha256_text(
                segment.normalized_text
            ):
                raise ValueError("segment text checksum does not match normalized text")
        for anchor in self.anchors:
            if (
                anchor.source_version_id != self.source_version_id
                or anchor.parse_job_id != self.parse_job_id
                or anchor.source_checksum != self.source_checksum
            ):
                raise ValueError("anchor binding does not match the immutable ParseJob")
        if Counter(anchor.excerpt_hash for anchor in self.anchors) != Counter(
            segment.text_checksum for segment in self.segments
        ):
            raise ValueError("anchor excerpts do not match the persisted segment set")
        if any(failure.parse_job_id != self.parse_job_id for failure in self.failure_units):
            raise ValueError("failure unit binding does not match the immutable ParseJob")
        if self.result_checksum != canonical_parse_result_checksum(
            source_checksum=self.source_checksum,
            segments=self.segments,
            anchors=self.anchors,
            failure_units=self.failure_units,
        ):
            raise ValueError("result checksum does not match the canonical manifest")
        return self


def _sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def canonical_parse_result_checksum(
    *,
    source_checksum: str,
    segments: tuple[DocumentSegment, ...] | list[DocumentSegment],
    anchors: tuple[SourceAnchor, ...] | list[SourceAnchor],
    failure_units: tuple[ParseFailureUnit, ...] | list[ParseFailureUnit],
) -> str:
    payload = {
        "source_checksum": source_checksum,
        "segments": [segment.model_dump(mode="json") for segment in segments],
        "anchors": [anchor.model_dump(mode="json") for anchor in anchors],
        "failures": [failure.model_dump(mode="json") for failure in failure_units],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


class SourceUploadCreate(ContractModel):
    filename: str = Field(min_length=1, max_length=512)
    content_type: str = Field(min_length=1, max_length=255)
    expected_size: int = Field(ge=1, le=536_870_912)
    expected_checksum: Sha256
    display_name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=4000)
    classification: DataClassification
    source_level: str | None = Field(default=None, max_length=128)
    tags: tuple[str, ...] = Field(default=(), max_length=64)
    valid_until: datetime | None = None
    source_document_id: UUID7 | None = None
    supersedes_source_version_id: UUID7 | None = None
    import_batch_id: UUID7 | None = None


class SourceUploadSessionResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    source_document_id: UUID7
    source_version_id: UUID7
    import_batch_id: UUID7 | None
    filename: str
    content_type: str
    expected_size: int
    expected_checksum: Sha256
    object_key: str
    status: SourceUploadStatus
    version: int = Field(ge=1)
    upload_url: str
    expires_at: datetime
    created_at: datetime


class SourceUploadComplete(ContractModel):
    checksum: Sha256
    size: int = Field(ge=1)


class SourceUploadCompleteResponse(ContractModel):
    source_id: UUID7
    source_version_id: UUID7
    parse_job_id: UUID7
    workflow_id: str
    run_id: str | None
    duplicate_source_version_ids: tuple[UUID7, ...] = ()
    source_status: SourceDocumentStatus
    version_status: SourceVersionState


class SourceDocumentResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    display_name: str
    description: str
    classification: DataClassification
    source_level: str | None
    tags: tuple[str, ...]
    valid_until: datetime | None
    status: SourceDocumentStatus
    version: int
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7
    versions: tuple[SourceVersionResponse, ...] = ()


class SourceVersionResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    source_document_id: UUID7
    filename: str
    content_type: str
    size: int
    checksum: Sha256
    object_version_id: str | None
    classification: DataClassification
    status: SourceVersionState
    version: int
    active_parse_job_id: UUID7 | None
    latest_parse_job_id: UUID7 | None
    supersedes_source_version_id: UUID7 | None
    created_at: datetime
    created_by: UUID7


class ParseJobResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    source_version_id: UUID7
    status: ParseJobStatus
    version: int
    parser_id: str
    parser_version: str
    config_checksum: Sha256
    document_model_version: str
    locator_version: str
    ocr_provider_id: str | None
    ocr_provider_version: str | None
    workflow_id: str
    temporal_run_id: str | None
    result_checksum: Sha256 | None
    failure_units: tuple[ParseFailureUnit, ...] = ()
    created_at: datetime
    updated_at: datetime


class SourceListResponse(ContractModel):
    items: tuple[SourceDocumentResponse, ...]
    next_cursor: str | None = None


class SegmentListResponse(ContractModel):
    items: tuple[DocumentSegment, ...]
    next_cursor: str | None = None


class ImportBatchCreate(ContractModel):
    display_name: str = Field(min_length=1, max_length=255)


class ImportBatchItemResponse(ContractModel):
    id: UUID7
    upload_session_id: UUID7
    source_document_id: UUID7 | None
    source_version_id: UUID7 | None
    filename: str
    status: Literal["UPLOADING", "PROCESSING", "SUCCEEDED", "PARTIAL", "FAILED", "CANCELED"]
    error_code: str | None
    safe_detail: str | None
    created_at: datetime
    updated_at: datetime


class ImportBatchResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    display_name: str
    status: ImportBatchStatus
    version: int
    item_summary: dict[str, int] = Field(default_factory=dict)
    items: tuple[ImportBatchItemResponse, ...] = ()
    created_at: datetime
    created_by: UUID7


class ReparseRequest(ContractModel):
    parser_id: str = Field(default="nexweave.parser.builtin", min_length=1, max_length=128)
    parser_version: str = Field(default="1.0.0", min_length=1, max_length=64)
    config: ParserConfig = Field(default_factory=ParserConfig)
    ocr_provider_id: str | None = Field(default=None, max_length=128)
    ocr_provider_version: str | None = Field(default=None, max_length=64)


class SourceInvalidationCreate(ContractModel):
    reason_code: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=2000)
    policy_version: str = Field(min_length=1, max_length=128)


class SourceInvalidationResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    source_version_id: UUID7
    reason_code: str
    reason: str
    policy_version: str
    created_at: datetime
    created_by: UUID7


class PreviewLocatorResult(ContractModel):
    locator: Locator
    matched: bool
    safe_detail: str


class PreviewResponse(ContractModel):
    source_version_id: UUID7
    parse_job_id: UUID7
    anchor_id: UUID7 | None
    anchor_status: Literal["VALID", "STALE", "UNRESOLVED", "REVOKED"] | None
    content_type: Literal["text/plain", "text/html"]
    sanitized_content: str
    locator_results: tuple[PreviewLocatorResult, ...] = ()


SourceDocumentResponse.model_rebuild()
