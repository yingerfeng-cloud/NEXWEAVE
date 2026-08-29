"""Pure M3 Source/Parse aggregates and transition rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from nexweave_domain.states import DataClassification, LocatorStatus, SourceVersionState


class SourceRuleViolation(ValueError):
    """A Source command violates an immutable domain rule."""


class SourceDocumentStatus(StrEnum):
    REGISTERED = "REGISTERED"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class SourceUploadStatus(StrEnum):
    INITIATED = "INITIATED"
    UPLOADING = "UPLOADING"
    COMPLETING = "COMPLETING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    EXPIRED = "EXPIRED"


class ImportBatchStatus(StrEnum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    PARTIAL = "PARTIAL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class ParseJobStatus(StrEnum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PARTIAL_FAILED = "PARTIAL_FAILED"
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"
    CANCELED = "CANCELED"


class SegmentStatus(StrEnum):
    VALID = "VALID"
    INVALIDATED = "INVALIDATED"


class BlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    TABLE_CELL = "table-cell"
    FIGURE_REFERENCE = "image/figure-reference"
    PAGE_BOUNDARY = "page-boundary"


class FailureScope(StrEnum):
    DOCUMENT = "document"
    PAGE = "page"
    TABLE = "table"
    SHEET = "sheet"
    BLOCK = "block"


TERMINAL_PARSE_JOB_STATUSES = frozenset(
    {
        ParseJobStatus.PARTIAL_FAILED,
        ParseJobStatus.FAILED,
        ParseJobStatus.SUCCEEDED,
        ParseJobStatus.CANCELED,
    }
)


@dataclass(frozen=True, slots=True)
class SourceDocument:
    id: UUID
    tenant_id: UUID
    space_id: UUID
    display_name: str
    description: str
    classification: DataClassification
    status: SourceDocumentStatus
    version: int
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID

    def activate(self, actor_id: UUID, now: datetime) -> SourceDocument:
        if self.status is not SourceDocumentStatus.REGISTERED:
            raise SourceRuleViolation("only a registered source can be activated")
        return replace(
            self,
            status=SourceDocumentStatus.ACTIVE,
            version=self.version + 1,
            updated_at=now,
            updated_by=actor_id,
        )

    def archive(self, actor_id: UUID, now: datetime) -> SourceDocument:
        if self.status is SourceDocumentStatus.ARCHIVED:
            raise SourceRuleViolation("the source cannot be archived from its current state")
        return replace(
            self,
            status=SourceDocumentStatus.ARCHIVED,
            version=self.version + 1,
            updated_at=now,
            updated_by=actor_id,
        )


@dataclass(frozen=True, slots=True)
class SourceVersion:
    id: UUID
    tenant_id: UUID
    space_id: UUID
    source_document_id: UUID
    checksum_sha256: str
    object_key: str
    object_version_id: str | None
    content_type: str
    size: int
    classification: DataClassification
    status: SourceVersionState
    version: int
    active_parse_job_id: UUID | None
    latest_parse_job_id: UUID | None
    supersedes_source_version_id: UUID | None

    def begin_parse(self, parse_job_id: UUID) -> SourceVersion:
        if self.status is SourceVersionState.SUPERSEDED:
            raise SourceRuleViolation("a superseded version cannot start a new parse")
        if self.active_parse_job_id is not None:
            return replace(self, latest_parse_job_id=parse_job_id, version=self.version + 1)
        if self.status not in {SourceVersionState.STORED, SourceVersionState.FAILED}:
            raise SourceRuleViolation("initial parse cannot start from the current state")
        return replace(
            self,
            status=SourceVersionState.PARSING,
            latest_parse_job_id=parse_job_id,
            version=self.version + 1,
        )

    def finalize_parse(
        self, parse_job_id: UUID, job_status: ParseJobStatus, usable_segment_count: int
    ) -> SourceVersion:
        if job_status not in TERMINAL_PARSE_JOB_STATUSES:
            raise SourceRuleViolation("only a terminal ParseJob can finalize a version")
        if job_status is ParseJobStatus.PARTIAL_FAILED and usable_segment_count < 1:
            raise SourceRuleViolation("partial parse requires at least one usable segment")
        if job_status is ParseJobStatus.SUCCEEDED and usable_segment_count < 1:
            raise SourceRuleViolation("successful parse requires at least one usable segment")

        next_state = self.status
        next_active = self.active_parse_job_id
        if job_status is ParseJobStatus.SUCCEEDED:
            next_state, next_active = SourceVersionState.PARSED, parse_job_id
        elif job_status is ParseJobStatus.PARTIAL_FAILED:
            next_state, next_active = SourceVersionState.PARTIAL, parse_job_id
        elif self.active_parse_job_id is None and job_status is ParseJobStatus.FAILED:
            next_state = SourceVersionState.FAILED
        elif self.active_parse_job_id is None and job_status is ParseJobStatus.CANCELED:
            next_state = SourceVersionState.STORED
        return replace(
            self,
            status=next_state,
            active_parse_job_id=next_active,
            latest_parse_job_id=parse_job_id,
            version=self.version + 1,
        )


@dataclass(frozen=True, slots=True)
class ParseJob:
    id: UUID
    tenant_id: UUID
    space_id: UUID
    source_version_id: UUID
    status: ParseJobStatus
    version: int
    parser_id: str
    parser_version: str
    config_checksum: str
    document_model_version: str
    locator_version: str
    ocr_provider_id: str | None = None
    ocr_provider_version: str | None = None

    def queue(self) -> ParseJob:
        if self.status is not ParseJobStatus.CREATED:
            raise SourceRuleViolation("only a created ParseJob can be queued")
        return replace(self, status=ParseJobStatus.QUEUED, version=self.version + 1)

    def start(self) -> ParseJob:
        if self.status is not ParseJobStatus.QUEUED:
            raise SourceRuleViolation("only a queued ParseJob can run")
        return replace(self, status=ParseJobStatus.RUNNING, version=self.version + 1)

    def finish(self, status: ParseJobStatus, usable_segment_count: int) -> ParseJob:
        if self.status is not ParseJobStatus.RUNNING or status not in TERMINAL_PARSE_JOB_STATUSES:
            raise SourceRuleViolation("invalid ParseJob terminal transition")
        if status is ParseJobStatus.PARTIAL_FAILED and usable_segment_count < 1:
            raise SourceRuleViolation("partial parse requires at least one usable segment")
        if status is ParseJobStatus.FAILED and usable_segment_count:
            raise SourceRuleViolation("failed parse cannot retain usable segments")
        return replace(self, status=status, version=self.version + 1)


@dataclass(frozen=True, slots=True)
class AnchorBinding:
    id: UUID
    source_version_id: UUID
    source_checksum: str
    parse_job_id: UUID
    locator_version: str
    excerpt_hash: str
    status: LocatorStatus
    relocated_from_anchor_id: UUID | None = None

    def mark_unresolved(self) -> AnchorBinding:
        if self.status is LocatorStatus.REVOKED:
            raise SourceRuleViolation("a revoked anchor cannot be changed")
        return replace(self, status=LocatorStatus.UNRESOLVED)

    def relocate(self, replacement_id: UUID) -> AnchorBinding:
        if replacement_id == self.id:
            raise SourceRuleViolation("anchor relocation must create a new anchor")
        return replace(
            self, id=replacement_id, status=LocatorStatus.VALID, relocated_from_anchor_id=self.id
        )


def canonical_raw_key(
    tenant_id: UUID,
    space_id: UUID,
    source_document_id: UUID,
    source_version_id: UUID,
    checksum_sha256: str,
) -> str:
    digest = checksum_sha256.removeprefix("sha256:")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise SourceRuleViolation("checksum must be a lowercase SHA-256 digest")
    return f"raw/v1/{tenant_id}/{space_id}/{source_document_id}/{source_version_id}/{digest}"
