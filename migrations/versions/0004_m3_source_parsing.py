"""Add M3 Source, immutable Raw metadata and versioned parse results.

Revision ID: 0004_m3
Revises: 0003_m2
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_m3"
down_revision: str | None = "0003_m2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
UTC_NOW = sa.text("CURRENT_TIMESTAMP")
CLASSIFICATION = "('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'HIGHLY_RESTRICTED')"


def _scope_foreign_key() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", "space_id"],
        ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    op.create_table(
        "source_import_batches",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="CREATED"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        _scope_foreign_key(),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_source_batches_scope_id"),
        sa.CheckConstraint(
            "status IN ('CREATED','UPLOADING','PROCESSING','PARTIAL','SUCCEEDED','FAILED','CANCELED')",
            name="ck_source_batches_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_source_batches_version"),
    )
    op.create_index(
        "ix_source_batches_scope_created",
        "source_import_batches",
        ["tenant_id", "space_id", "created_at", "id"],
    )

    op.create_table(
        "source_documents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False, server_default=""),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("source_level", sa.String(128)),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False, server_default="REGISTERED"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        _scope_foreign_key(),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_source_documents_scope_id"),
        sa.CheckConstraint(
            "classification IN " + CLASSIFICATION, name="ck_source_documents_classification"
        ),
        sa.CheckConstraint(
            "status IN ('REGISTERED','ACTIVE','ARCHIVED')", name="ck_source_documents_status"
        ),
        sa.CheckConstraint("version >= 1", name="ck_source_documents_version"),
    )
    op.create_index(
        "ix_source_documents_scope_status_created",
        "source_documents",
        ["tenant_id", "space_id", "status", "created_at", "id"],
    )

    op.create_table(
        "source_upload_sessions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("source_document_id", UUID, nullable=False),
        sa.Column("source_version_id", UUID, nullable=False),
        sa.Column("import_batch_id", UUID),
        sa.Column("supersedes_source_version_id", UUID),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("expected_size", sa.BigInteger(), nullable=False),
        sa.Column("expected_checksum", sa.String(71), nullable=False),
        sa.Column("object_key", sa.String(2048), nullable=False),
        sa.Column("object_version_id", sa.String(1024)),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False, server_default=""),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("source_level", sa.String(128)),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False, server_default="INITIATED"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        _scope_foreign_key(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "import_batch_id"],
            [
                "source_import_batches.tenant_id",
                "source_import_batches.space_id",
                "source_import_batches.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_source_uploads_scope_id"),
        sa.UniqueConstraint(
            "tenant_id", "space_id", "source_version_id", name="uq_source_uploads_version"
        ),
        sa.UniqueConstraint("object_key", name="uq_source_uploads_object_key"),
        sa.CheckConstraint("expected_size > 0", name="ck_source_uploads_size"),
        sa.CheckConstraint(
            "expected_checksum ~ '^sha256:[0-9a-f]{64}$'", name="ck_source_uploads_checksum"
        ),
        sa.CheckConstraint(
            "classification IN " + CLASSIFICATION, name="ck_source_uploads_classification"
        ),
        sa.CheckConstraint(
            "status IN ('INITIATED','UPLOADING','COMPLETING','COMPLETED','ABORTED','EXPIRED')",
            name="ck_source_uploads_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_source_uploads_version"),
    )
    op.create_index(
        "ix_source_uploads_scope_status_expires",
        "source_upload_sessions",
        ["tenant_id", "space_id", "status", "expires_at"],
    )

    op.create_table(
        "source_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("source_document_id", UUID, nullable=False),
        sa.Column("upload_session_id", UUID, nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(71), nullable=False),
        sa.Column("object_key", sa.String(2048), nullable=False),
        sa.Column("object_version_id", sa.String(1024)),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="STORED"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("active_parse_job_id", UUID),
        sa.Column("latest_parse_job_id", UUID),
        sa.Column("supersedes_source_version_id", UUID),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_foreign_key(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "source_document_id"],
            ["source_documents.tenant_id", "source_documents.space_id", "source_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "upload_session_id"],
            [
                "source_upload_sessions.tenant_id",
                "source_upload_sessions.space_id",
                "source_upload_sessions.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "supersedes_source_version_id"],
            ["source_versions.tenant_id", "source_versions.space_id", "source_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_source_versions_scope_id"),
        sa.UniqueConstraint(
            "tenant_id", "space_id", "id", "checksum", name="uq_source_versions_scope_checksum"
        ),
        sa.UniqueConstraint("object_key", name="uq_source_versions_object_key"),
        sa.UniqueConstraint("upload_session_id", name="uq_source_versions_upload"),
        sa.CheckConstraint("size > 0", name="ck_source_versions_size"),
        sa.CheckConstraint(
            "checksum ~ '^sha256:[0-9a-f]{64}$'", name="ck_source_versions_checksum"
        ),
        sa.CheckConstraint("object_key ~ '^raw/v1/'", name="ck_source_versions_raw_key"),
        sa.CheckConstraint(
            "classification IN " + CLASSIFICATION, name="ck_source_versions_classification"
        ),
        sa.CheckConstraint(
            "status IN ('STORED','PARSING','PARTIAL','PARSED','FAILED','SUPERSEDED')",
            name="ck_source_versions_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_source_versions_version"),
        sa.CheckConstraint(
            "supersedes_source_version_id IS NULL OR supersedes_source_version_id <> id",
            name="ck_source_versions_no_self_supersede",
        ),
    )
    op.create_index(
        "ix_source_versions_document_created",
        "source_versions",
        ["tenant_id", "space_id", "source_document_id", "created_at", "id"],
    )
    op.create_index(
        "ix_source_versions_scope_checksum",
        "source_versions",
        ["tenant_id", "space_id", "checksum"],
    )
    op.create_index(
        "uq_source_versions_one_replacement",
        "source_versions",
        ["tenant_id", "space_id", "supersedes_source_version_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_source_version_id IS NOT NULL"),
    )

    op.create_table(
        "parse_jobs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("source_version_id", UUID, nullable=False),
        sa.Column("workflow_task_id", UUID),
        sa.Column("workflow_id", sa.String(768), nullable=False),
        sa.Column("temporal_run_id", sa.String(255)),
        sa.Column("status", sa.String(32), nullable=False, server_default="CREATED"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("parser_id", sa.String(128), nullable=False),
        sa.Column("parser_version", sa.String(64), nullable=False),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("config_checksum", sa.String(71), nullable=False),
        sa.Column("document_model_version", sa.String(64), nullable=False),
        sa.Column("locator_version", sa.String(64), nullable=False),
        sa.Column("ocr_provider_id", sa.String(128)),
        sa.Column("ocr_provider_version", sa.String(64)),
        sa.Column("malware_scan_status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column(
            "malware_scanner_provider", sa.String(128), nullable=False, server_default="clamav"
        ),
        sa.Column("malware_scanner_version", sa.String(64), nullable=False, server_default="1.4.3"),
        sa.Column("malware_policy_version", sa.String(128), nullable=False, server_default="m3-v1"),
        sa.Column("result_checksum", sa.String(71)),
        sa.Column("result_stats", JSONB, nullable=False, server_default="{}"),
        sa.Column("error_code", sa.String(128)),
        sa.Column("error_detail", sa.String(1024)),
        sa.Column("correlation_id", UUID, nullable=False),
        sa.Column("trace_id", sa.String(64)),
        sa.Column("requested_by_actor_type", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        _scope_foreign_key(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "source_version_id"],
            ["source_versions.tenant_id", "source_versions.space_id", "source_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "workflow_task_id"],
            ["workflow_tasks.tenant_id", "workflow_tasks.space_id", "workflow_tasks.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_parse_jobs_scope_id"),
        sa.UniqueConstraint(
            "tenant_id", "space_id", "id", "source_version_id", name="uq_parse_jobs_scope_source"
        ),
        sa.UniqueConstraint("workflow_id", name="uq_parse_jobs_workflow_id"),
        sa.CheckConstraint(
            "status IN ('CREATED','QUEUED','RUNNING','PARTIAL_FAILED','FAILED','SUCCEEDED','CANCELED')",
            name="ck_parse_jobs_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_parse_jobs_version"),
        sa.CheckConstraint(
            "malware_scan_status IN ('PENDING','CLEAN','INFECTED','FAILED')",
            name="ck_parse_jobs_malware_scan_status",
        ),
        sa.CheckConstraint(
            "requested_by_actor_type IN ('USER','SERVICE')",
            name="ck_parse_jobs_requested_actor_type",
        ),
        sa.CheckConstraint(
            "config_checksum ~ '^sha256:[0-9a-f]{64}$'", name="ck_parse_jobs_config_checksum"
        ),
        sa.CheckConstraint(
            "result_checksum IS NULL OR result_checksum ~ '^sha256:[0-9a-f]{64}$'",
            name="ck_parse_jobs_result_checksum",
        ),
    )
    op.create_index(
        "ix_parse_jobs_source_created",
        "parse_jobs",
        ["tenant_id", "space_id", "source_version_id", "created_at", "id"],
    )

    op.create_table(
        "source_import_batch_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("import_batch_id", UUID, nullable=False),
        sa.Column("upload_session_id", UUID, nullable=False),
        sa.Column("source_document_id", UUID),
        sa.Column("source_version_id", UUID),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="UPLOADING"),
        sa.Column("error_code", sa.String(128)),
        sa.Column("safe_detail", sa.String(1024)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        _scope_foreign_key(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "import_batch_id"],
            [
                "source_import_batches.tenant_id",
                "source_import_batches.space_id",
                "source_import_batches.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "upload_session_id"],
            [
                "source_upload_sessions.tenant_id",
                "source_upload_sessions.space_id",
                "source_upload_sessions.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "source_document_id"],
            ["source_documents.tenant_id", "source_documents.space_id", "source_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "source_version_id"],
            ["source_versions.tenant_id", "source_versions.space_id", "source_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_source_batch_items_scope_id"),
        sa.UniqueConstraint("upload_session_id", name="uq_source_batch_items_upload"),
        sa.CheckConstraint(
            "status IN ('UPLOADING','PROCESSING','SUCCEEDED','PARTIAL','FAILED','CANCELED')",
            name="ck_source_batch_items_status",
        ),
        sa.CheckConstraint(
            "(source_document_id IS NULL) = (source_version_id IS NULL)",
            name="ck_source_batch_items_source_pair",
        ),
    )
    op.create_index(
        "ix_source_batch_items_batch_status",
        "source_import_batch_items",
        ["tenant_id", "space_id", "import_batch_id", "status", "created_at", "id"],
    )

    op.create_foreign_key(
        "fk_source_versions_active_parse_job",
        "source_versions",
        "parse_jobs",
        ["tenant_id", "space_id", "active_parse_job_id", "id"],
        ["tenant_id", "space_id", "id", "source_version_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_source_versions_latest_parse_job",
        "source_versions",
        "parse_jobs",
        ["tenant_id", "space_id", "latest_parse_job_id", "id"],
        ["tenant_id", "space_id", "id", "source_version_id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "source_invalidations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("source_version_id", UUID, nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("policy_version", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "source_version_id"],
            ["source_versions.tenant_id", "source_versions.space_id", "source_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_source_invalidations_scope_id"),
    )
    op.create_index(
        "ix_source_invalidations_version_created",
        "source_invalidations",
        ["tenant_id", "space_id", "source_version_id", "created_at", "id"],
    )

    op.create_table(
        "parse_failure_units",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("parse_job_id", UUID, nullable=False),
        sa.Column("error_code", sa.String(128), nullable=False),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("scope_ref", sa.String(512), nullable=False),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("safe_detail", sa.String(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "parse_job_id"],
            ["parse_jobs.tenant_id", "parse_jobs.space_id", "parse_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("parse_job_id", "id", name="uq_parse_failure_units_job_id"),
        sa.CheckConstraint(
            "scope IN ('document','page','table','sheet','block')",
            name="ck_parse_failure_units_scope",
        ),
    )

    op.create_table(
        "document_segments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("source_version_id", UUID, nullable=False),
        sa.Column("parse_job_id", UUID, nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("block_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="VALID"),
        sa.Column("structure_path", sa.String(2048), nullable=False),
        sa.Column("normalized_text", sa.Text()),
        sa.Column("derived_object_key", sa.String(2048)),
        sa.Column("text_checksum", sa.String(71), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("sheet_name", sa.String(255)),
        sa.Column("table_id", sa.String(512)),
        sa.Column("row_index", sa.Integer()),
        sa.Column("column_index", sa.Integer()),
        sa.Column("locators", JSONB, nullable=False),
        sa.Column("parser_id", sa.String(128), nullable=False),
        sa.Column("parser_version", sa.String(64), nullable=False),
        sa.Column("config_checksum", sa.String(71), nullable=False),
        sa.Column("document_model_version", sa.String(64), nullable=False),
        sa.Column("locator_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "parse_job_id", "source_version_id"],
            [
                "parse_jobs.tenant_id",
                "parse_jobs.space_id",
                "parse_jobs.id",
                "parse_jobs.source_version_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_document_segments_scope_id"),
        sa.UniqueConstraint("parse_job_id", "sequence", name="uq_document_segments_job_sequence"),
        sa.CheckConstraint("sequence >= 0", name="ck_document_segments_sequence"),
        sa.CheckConstraint("status IN ('VALID','INVALIDATED')", name="ck_document_segments_status"),
        sa.CheckConstraint(
            "normalized_text IS NOT NULL OR derived_object_key IS NOT NULL",
            name="ck_document_segments_content",
        ),
        sa.CheckConstraint(
            "text_checksum ~ '^sha256:[0-9a-f]{64}$'", name="ck_document_segments_text_checksum"
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number >= 1", name="ck_document_segments_page"
        ),
        sa.CheckConstraint("row_index IS NULL OR row_index >= 0", name="ck_document_segments_row"),
        sa.CheckConstraint(
            "column_index IS NULL OR column_index >= 0", name="ck_document_segments_column"
        ),
    )
    op.create_index(
        "ix_document_segments_job_sequence",
        "document_segments",
        ["tenant_id", "space_id", "parse_job_id", "sequence"],
    )

    op.create_table(
        "source_anchors",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("source_version_id", UUID, nullable=False),
        sa.Column("source_checksum", sa.String(71), nullable=False),
        sa.Column("parse_job_id", UUID, nullable=False),
        sa.Column("locator_version", sa.String(64), nullable=False),
        sa.Column("excerpt_hash", sa.String(71), nullable=False),
        sa.Column("locators", JSONB, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="VALID"),
        sa.Column("relocated_from_anchor_id", UUID),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "source_version_id", "source_checksum"],
            [
                "source_versions.tenant_id",
                "source_versions.space_id",
                "source_versions.id",
                "source_versions.checksum",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "parse_job_id", "source_version_id"],
            [
                "parse_jobs.tenant_id",
                "parse_jobs.space_id",
                "parse_jobs.id",
                "parse_jobs.source_version_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "relocated_from_anchor_id"],
            ["source_anchors.tenant_id", "source_anchors.space_id", "source_anchors.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_source_anchors_scope_id"),
        sa.CheckConstraint(
            "source_checksum ~ '^sha256:[0-9a-f]{64}$'", name="ck_source_anchors_checksum"
        ),
        sa.CheckConstraint(
            "excerpt_hash ~ '^sha256:[0-9a-f]{64}$'", name="ck_source_anchors_excerpt_hash"
        ),
        sa.CheckConstraint(
            "status IN ('VALID','STALE','UNRESOLVED','REVOKED')", name="ck_source_anchors_status"
        ),
        sa.CheckConstraint("jsonb_array_length(locators) > 0", name="ck_source_anchors_locators"),
        sa.CheckConstraint(
            "relocated_from_anchor_id IS NULL OR relocated_from_anchor_id <> id",
            name="ck_source_anchors_no_self_relocation",
        ),
    )
    op.create_index(
        "ix_source_anchors_version_job",
        "source_anchors",
        ["tenant_id", "space_id", "source_version_id", "parse_job_id"],
    )

    op.execute(
        """
        CREATE FUNCTION prevent_nexweave_m3_fact_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in ("source_invalidations", "parse_failure_units", "document_segments"):
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_nexweave_m3_fact_mutation()"
        )
    op.execute(
        """
        CREATE FUNCTION protect_nexweave_source_anchor() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'source_anchors are not deletable';
          END IF;
          IF NEW.tenant_id <> OLD.tenant_id OR NEW.space_id <> OLD.space_id
             OR NEW.source_version_id <> OLD.source_version_id
             OR NEW.source_checksum <> OLD.source_checksum
             OR NEW.parse_job_id <> OLD.parse_job_id
             OR NEW.locator_version <> OLD.locator_version
             OR NEW.excerpt_hash <> OLD.excerpt_hash
             OR NEW.locators <> OLD.locators
             OR NEW.relocated_from_anchor_id IS DISTINCT FROM OLD.relocated_from_anchor_id
             OR NEW.created_at <> OLD.created_at OR NEW.created_by <> OLD.created_by THEN
            RAISE EXCEPTION 'SourceAnchor locator facts are immutable';
          END IF;
          IF NOT (
            NEW.status = OLD.status
            OR (OLD.status = 'VALID' AND NEW.status IN ('STALE','UNRESOLVED','REVOKED'))
            OR (OLD.status = 'STALE' AND NEW.status IN ('UNRESOLVED','REVOKED'))
            OR (OLD.status = 'UNRESOLVED' AND NEW.status = 'REVOKED')
          ) THEN
            RAISE EXCEPTION 'SourceAnchor status transition is invalid';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER source_anchors_protect BEFORE UPDATE OR DELETE ON source_anchors "
        "FOR EACH ROW EXECUTE FUNCTION protect_nexweave_source_anchor()"
    )
    op.execute(
        """
        CREATE FUNCTION enforce_nexweave_source_classification() RETURNS trigger AS $$
        DECLARE document_classification text;
        BEGIN
          SELECT classification INTO document_classification
          FROM source_documents
          WHERE tenant_id = NEW.tenant_id AND space_id = NEW.space_id
            AND id = NEW.source_document_id;
          IF document_classification IS NULL OR NEW.classification <> document_classification THEN
            RAISE EXCEPTION 'SourceVersion classification must equal SourceDocument classification';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER source_versions_classification_guard "
        "BEFORE INSERT OR UPDATE OF classification,source_document_id ON source_versions "
        "FOR EACH ROW EXECUTE FUNCTION enforce_nexweave_source_classification()"
    )
    op.execute(
        """
        CREATE FUNCTION protect_nexweave_raw_metadata() RETURNS trigger AS $$
        BEGIN
          IF NEW.checksum <> OLD.checksum OR NEW.object_key <> OLD.object_key
             OR NEW.object_version_id IS DISTINCT FROM OLD.object_version_id
             OR NEW.size <> OLD.size OR NEW.content_type <> OLD.content_type
             OR NEW.filename <> OLD.filename OR NEW.classification <> OLD.classification THEN
            RAISE EXCEPTION 'SourceVersion Raw metadata is immutable';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER source_versions_protect_raw BEFORE UPDATE ON source_versions "
        "FOR EACH ROW EXECUTE FUNCTION protect_nexweave_raw_metadata()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER source_versions_protect_raw ON source_versions")
    op.execute("DROP FUNCTION protect_nexweave_raw_metadata")
    op.execute("DROP TRIGGER source_versions_classification_guard ON source_versions")
    op.execute("DROP FUNCTION enforce_nexweave_source_classification")
    op.execute("DROP TRIGGER source_anchors_protect ON source_anchors")
    op.execute("DROP FUNCTION protect_nexweave_source_anchor")
    for table in ("document_segments", "parse_failure_units", "source_invalidations"):
        op.execute(f"DROP TRIGGER {table}_append_only ON {table}")
    op.execute("DROP FUNCTION prevent_nexweave_m3_fact_mutation")
    op.drop_index("ix_source_anchors_version_job", table_name="source_anchors")
    op.drop_table("source_anchors")
    op.drop_index("ix_document_segments_job_sequence", table_name="document_segments")
    op.drop_table("document_segments")
    op.drop_table("parse_failure_units")
    op.drop_index("ix_source_invalidations_version_created", table_name="source_invalidations")
    op.drop_table("source_invalidations")
    op.drop_constraint("fk_source_versions_latest_parse_job", "source_versions", type_="foreignkey")
    op.drop_constraint("fk_source_versions_active_parse_job", "source_versions", type_="foreignkey")
    op.drop_index("ix_source_batch_items_batch_status", table_name="source_import_batch_items")
    op.drop_table("source_import_batch_items")
    op.drop_index("ix_parse_jobs_source_created", table_name="parse_jobs")
    op.drop_table("parse_jobs")
    op.drop_index("ix_source_versions_scope_checksum", table_name="source_versions")
    op.drop_index("uq_source_versions_one_replacement", table_name="source_versions")
    op.drop_index("ix_source_versions_document_created", table_name="source_versions")
    op.drop_table("source_versions")
    op.drop_index("ix_source_uploads_scope_status_expires", table_name="source_upload_sessions")
    op.drop_table("source_upload_sessions")
    op.drop_index("ix_source_documents_scope_status_created", table_name="source_documents")
    op.drop_table("source_documents")
    op.drop_index("ix_source_batches_scope_created", table_name="source_import_batches")
    op.drop_table("source_import_batches")
