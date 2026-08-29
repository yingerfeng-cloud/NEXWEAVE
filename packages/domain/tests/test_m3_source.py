from datetime import UTC, datetime

import pytest

from nexweave_domain import (
    DataClassification,
    ParseJob,
    ParseJobStatus,
    SourceDocument,
    SourceDocumentStatus,
    SourceRuleViolation,
    SourceVersion,
    SourceVersionState,
    canonical_raw_key,
    new_uuid7,
)


def test_raw_key_and_source_document_archive_are_explicit() -> None:
    tenant_id, space_id, source_id, version_id, actor_id = (new_uuid7() for _ in range(5))
    checksum = "sha256:" + "a" * 64
    assert canonical_raw_key(tenant_id, space_id, source_id, version_id, checksum) == (
        f"raw/v1/{tenant_id}/{space_id}/{source_id}/{version_id}/{'a' * 64}"
    )
    now = datetime.now(UTC)
    source = SourceDocument(
        id=source_id,
        tenant_id=tenant_id,
        space_id=space_id,
        display_name="Synthetic manual",
        description="",
        classification=DataClassification.INTERNAL,
        status=SourceDocumentStatus.REGISTERED,
        version=1,
        created_at=now,
        created_by=actor_id,
        updated_at=now,
        updated_by=actor_id,
    )
    assert (
        source.activate(actor_id, now).archive(actor_id, now).status
        is SourceDocumentStatus.ARCHIVED
    )


def test_partial_requires_output_and_reparse_failure_preserves_active() -> None:
    tenant_id, space_id, source_id, version_id, active_job_id, failed_job_id = (
        new_uuid7() for _ in range(6)
    )
    source_version = SourceVersion(
        id=version_id,
        tenant_id=tenant_id,
        space_id=space_id,
        source_document_id=source_id,
        checksum_sha256="sha256:" + "b" * 64,
        object_key=f"raw/v1/{tenant_id}/{space_id}/{source_id}/{version_id}/{'b' * 64}",
        object_version_id="object-version-1",
        content_type="text/plain",
        size=4,
        classification=DataClassification.INTERNAL,
        status=SourceVersionState.PARSED,
        version=2,
        active_parse_job_id=active_job_id,
        latest_parse_job_id=active_job_id,
        supersedes_source_version_id=None,
    )
    failed = source_version.begin_parse(failed_job_id).finalize_parse(
        failed_job_id, ParseJobStatus.FAILED, 0
    )
    assert failed.status is SourceVersionState.PARSED
    assert failed.active_parse_job_id == active_job_id
    assert failed.latest_parse_job_id == failed_job_id

    job = ParseJob(
        id=failed_job_id,
        tenant_id=tenant_id,
        space_id=space_id,
        source_version_id=version_id,
        status=ParseJobStatus.RUNNING,
        version=3,
        parser_id="builtin",
        parser_version="1",
        config_checksum="sha256:" + "c" * 64,
        document_model_version="1.0",
        locator_version="1.0",
    )
    with pytest.raises(SourceRuleViolation):
        job.finish(ParseJobStatus.PARTIAL_FAILED, 0)
