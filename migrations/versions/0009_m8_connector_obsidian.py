"""Add M8 Connector executions and Obsidian exchange facts.

Revision ID: 0009_m8
Revises: 0008_m7
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_m8"
down_revision: str | None = "0008_m7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
UTC_NOW = sa.text("CURRENT_TIMESTAMP")


def _scope_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", "space_id"],
        ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    op.drop_constraint("ck_workflow_tasks_type", "workflow_tasks", type_="check")
    op.create_check_constraint(
        "ck_workflow_tasks_type",
        "workflow_tasks",
        "workflow_type IN ('SOURCE_INGESTION','KNOWLEDGE_COMPILE','HUMAN_REVIEW','QUALITY_EVALUATION','KNOWLEDGE_RELEASE','DOMAIN_PACK_INSTALL','GRIDCREW_FEEDBACK_INGESTION','CONNECTOR_SYNC')",
    )
    op.create_table(
        "connector_instances",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("definition_id", UUID, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("credential_ref", sa.String(512)),
        sa.Column("allowlist", JSONB, nullable=False),
        sa.Column("config", JSONB, nullable=False),
        sa.Column("field_mapping", JSONB, nullable=False),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("config_checksum", sa.String(71), nullable=False),
        sa.Column("watermark", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["definition_id"], ["connector_definitions.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "name", name="uq_connector_instances_name"),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_connector_instances_scope_id"),
        sa.CheckConstraint(
            "kind IN ('FILESYSTEM','S3','WEB_REST','GIT')", name="ck_connector_instances_kind"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','ACTIVE','PAUSED','FAILED','REVOKED')",
            name="ck_connector_instances_status",
        ),
        sa.CheckConstraint(
            "classification IN ('PUBLIC','INTERNAL','CONFIDENTIAL','HIGHLY_RESTRICTED')",
            name="ck_connector_instances_classification",
        ),
        sa.CheckConstraint(
            "config_checksum ~ '^sha256:[0-9a-f]{64}$'", name="ck_connector_instances_checksum"
        ),
    )
    op.create_table(
        "connector_sync_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("connector_instance_id", UUID, nullable=False),
        sa.Column("workflow_task_id", UUID, nullable=False),
        sa.Column("workflow_id", sa.String(768), nullable=False),
        sa.Column("temporal_run_id", sa.String(255)),
        sa.Column("status", sa.String(24), nullable=False, server_default="CREATED"),
        sa.Column(
            "requested_watermark", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "resulting_watermark", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("result_summary", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_code", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "connector_instance_id"],
            [
                "connector_instances.tenant_id",
                "connector_instances.space_id",
                "connector_instances.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["workflow_task_id"], ["workflow_tasks.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("workflow_task_id", name="uq_connector_sync_runs_task"),
        sa.UniqueConstraint("workflow_id", name="uq_connector_sync_runs_workflow"),
        sa.CheckConstraint(
            "status IN ('CREATED','RUNNING','PARTIAL_FAILED','FAILED','SUCCEEDED','CANCELED')",
            name="ck_connector_sync_runs_status",
        ),
    )
    op.create_table(
        "obsidian_exports",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("wiki_page_id", UUID, nullable=False),
        sa.Column("wiki_page_version_id", UUID, nullable=False),
        sa.Column("content_checksum", sa.String(71), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(["wiki_page_id"], ["wiki_pages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["wiki_page_version_id"], ["wiki_page_versions.id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "obsidian_imports",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("wiki_page_id", UUID),
        sa.Column("base_version_id", UUID),
        sa.Column("draft_version_id", UUID),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("markdown_checksum", sa.String(71), nullable=False),
        sa.Column("markdown_diff", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(["wiki_page_id"], ["wiki_pages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["base_version_id"], ["wiki_page_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["draft_version_id"], ["wiki_page_versions.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT_CREATED','CONFLICT')", name="ck_obsidian_imports_status"
        ),
    )
    op.create_table(
        "obsidian_import_conflicts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("import_id", UUID, nullable=False),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("details", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        _scope_fk(),
        sa.ForeignKeyConstraint(["import_id"], ["obsidian_imports.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("import_id", name="uq_obsidian_import_conflicts_import"),
    )


def downgrade() -> None:
    op.drop_table("obsidian_import_conflicts")
    op.drop_table("obsidian_imports")
    op.drop_table("obsidian_exports")
    op.drop_table("connector_sync_runs")
    op.drop_table("connector_instances")
    op.drop_constraint("ck_workflow_tasks_type", "workflow_tasks", type_="check")
    op.create_check_constraint(
        "ck_workflow_tasks_type",
        "workflow_tasks",
        "workflow_type IN ('SOURCE_INGESTION','KNOWLEDGE_COMPILE','HUMAN_REVIEW','QUALITY_EVALUATION','KNOWLEDGE_RELEASE','DOMAIN_PACK_INSTALL','GRIDCREW_FEEDBACK_INGESTION')",
    )
