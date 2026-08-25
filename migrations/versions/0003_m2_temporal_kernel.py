"""Add M2 Temporal task projections and append-only workflow event log.

Revision ID: 0003_m2
Revises: 0002_m1
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_m2"
down_revision: str | None = "0002_m1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
UTC_NOW = sa.text("CURRENT_TIMESTAMP")
WORKFLOW_TYPES = (
    "('SOURCE_INGESTION', 'KNOWLEDGE_COMPILE', 'HUMAN_REVIEW', "
    "'QUALITY_EVALUATION', 'KNOWLEDGE_RELEASE', 'DOMAIN_PACK_INSTALL', "
    "'GRIDCREW_FEEDBACK_INGESTION')"
)
TASK_STATUSES = (
    "('CREATED', 'STARTING', 'RUNNING', 'PAUSED', 'WAITING', 'WAITING_INPUT', "
    "'CANCELLING', 'COMPENSATING', 'CANCELLED', 'SUCCEEDED', 'FAILED', "
    "'TIMED_OUT', 'REJECTED')"
)
STEP_STATUSES = (
    "('PENDING', 'RUNNING', 'RETRYING', 'PAUSED', 'WAITING', 'SUCCEEDED', "
    "'FAILED', 'CANCELLED', 'COMPENSATED')"
)


def upgrade() -> None:
    op.create_table(
        "workflow_tasks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("workflow_type", sa.String(64), nullable=False),
        sa.Column("business_key", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("workflow_id", sa.String(768), nullable=False),
        sa.Column("temporal_run_id", sa.String(255)),
        sa.Column("status", sa.String(32), nullable=False, server_default="CREATED"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_step", sa.String(255)),
        sa.Column("input_refs", JSONB, nullable=False, server_default="{}"),
        sa.Column("start_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("result_summary", JSONB, nullable=False, server_default="{}"),
        sa.Column("error_code", sa.String(128)),
        sa.Column("error_detail", sa.String(2000)),
        sa.Column("projection_revision", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("projection_in_sync", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id"],
            ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_workflow_tasks_scope_id"),
        sa.UniqueConstraint("workflow_id", name="uq_workflow_tasks_workflow_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "space_id",
            "workflow_type",
            "business_key",
            name="uq_workflow_tasks_business_key",
        ),
        sa.CheckConstraint(f"workflow_type IN {WORKFLOW_TYPES}", name="ck_workflow_tasks_type"),
        sa.CheckConstraint(f"status IN {TASK_STATUSES}", name="ck_workflow_tasks_status"),
        sa.CheckConstraint("version >= 1", name="ck_workflow_tasks_version"),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_workflow_tasks_progress"),
        sa.CheckConstraint(
            "projection_revision >= 0", name="ck_workflow_tasks_projection_revision"
        ),
    )
    op.create_index(
        "ix_workflow_tasks_tenant_space_created",
        "workflow_tasks",
        ["tenant_id", "space_id", "created_at", "id"],
    )
    op.create_index(
        "ix_workflow_tasks_tenant_status",
        "workflow_tasks",
        ["tenant_id", "status", "updated_at"],
    )

    op.create_table(
        "workflow_steps",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("task_id", UUID, nullable=False),
        sa.Column("step_key", sa.String(255), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.String(2000), nullable=False, server_default=""),
        sa.Column("error_code", sa.String(128)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "task_id"],
            ["workflow_tasks.tenant_id", "workflow_tasks.space_id", "workflow_tasks.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("task_id", "step_key", name="uq_workflow_steps_task_step"),
        sa.CheckConstraint(f"status IN {STEP_STATUSES}", name="ck_workflow_steps_status"),
        sa.CheckConstraint("sequence >= 0", name="ck_workflow_steps_sequence"),
        sa.CheckConstraint("attempt >= 0", name="ck_workflow_steps_attempt"),
    )
    op.create_index("ix_workflow_steps_task_sequence", "workflow_steps", ["task_id", "sequence"])

    op.create_table(
        "workflow_task_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("task_id", UUID, nullable=False),
        sa.Column("event_key", sa.String(512), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("workflow_status", sa.String(32), nullable=False),
        sa.Column("step_key", sa.String(255)),
        sa.Column("message", sa.String(2000), nullable=False, server_default=""),
        sa.Column("details", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "task_id"],
            ["workflow_tasks.tenant_id", "workflow_tasks.space_id", "workflow_tasks.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("task_id", "event_key", name="uq_workflow_task_events_key"),
        sa.CheckConstraint(
            f"workflow_status IN {TASK_STATUSES}", name="ck_workflow_task_events_status"
        ),
    )
    op.create_index(
        "ix_workflow_task_events_task_time",
        "workflow_task_events",
        ["task_id", "occurred_at", "id"],
    )
    op.execute(
        """
        CREATE FUNCTION prevent_nexweave_workflow_event_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'workflow task events are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER workflow_task_events_append_only
        BEFORE UPDATE OR DELETE ON workflow_task_events
        FOR EACH ROW EXECUTE FUNCTION prevent_nexweave_workflow_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER workflow_task_events_append_only ON workflow_task_events")
    op.execute("DROP FUNCTION prevent_nexweave_workflow_event_mutation")
    op.drop_index("ix_workflow_task_events_task_time", table_name="workflow_task_events")
    op.drop_table("workflow_task_events")
    op.drop_index("ix_workflow_steps_task_sequence", table_name="workflow_steps")
    op.drop_table("workflow_steps")
    op.drop_index("ix_workflow_tasks_tenant_status", table_name="workflow_tasks")
    op.drop_index("ix_workflow_tasks_tenant_space_created", table_name="workflow_tasks")
    op.drop_table("workflow_tasks")
