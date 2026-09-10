"""Add M6 governed Claims, Evidence, Conflicts and HumanReview facts.

Revision ID: 0007_m6
Revises: 0006_m5
Create Date: 2026-08-30
"""
# ruff: noqa: E501

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_m6"
down_revision: str | None = "0006_m5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
UTC_NOW = sa.text("CURRENT_TIMESTAMP")
CHECKSUM = r"^sha256:[0-9a-f]{64}$"
STABLE_KEY = r"^[a-z][a-z0-9.-]{1,62}/[a-z][a-z0-9-]{0,62}$"


def _scope_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", "space_id"],
        ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    op.create_table(
        "review_policies",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("stages", JSONB, nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("escalation_role", sa.String(32), nullable=False),
        sa.Column("allow_batch", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("batch_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "source_authority_rules", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.UniqueConstraint("space_id", "risk_level", "version", name="uq_review_policies_version"),
        sa.CheckConstraint("risk_level IN ('LOW','MEDIUM','HIGH')", name="ck_review_policies_risk"),
        sa.CheckConstraint("timeout_seconds >= 60", name="ck_review_policies_timeout"),
        sa.CheckConstraint("batch_limit BETWEEN 1 AND 100", name="ck_review_policies_batch"),
        sa.CheckConstraint("status IN ('ACTIVE','RETIRED')", name="ck_review_policies_status"),
    )
    op.create_table(
        "claims",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("candidate_id", UUID, nullable=False),
        sa.Column("subject_entity_id", UUID, nullable=False),
        sa.Column("predicate_key", sa.String(126), nullable=False),
        sa.Column("object_value", JSONB, nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("scope", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("confidence_level", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="APPROVED"),
        sa.Column("provenance", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(["candidate_id"], ["claim_candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "subject_entity_id"],
            [
                "knowledge_entities.tenant_id",
                "knowledge_entities.space_id",
                "knowledge_entities.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("candidate_id", name="uq_claims_candidate"),
        sa.CheckConstraint(f"predicate_key ~ '{STABLE_KEY}'", name="ck_claims_predicate"),
        sa.CheckConstraint(
            "confidence_level IN ('LOW','MEDIUM','HIGH')", name="ck_claims_confidence"
        ),
        sa.CheckConstraint(
            "status IN ('APPROVED','SUPERSEDED','REJECTED')", name="ck_claims_status"
        ),
    )
    op.create_table(
        "evidence_records",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("claim_id", UUID),
        sa.Column("relation_candidate_id", UUID),
        sa.Column("source_anchor_id", UUID, nullable=False),
        sa.Column("stance", sa.String(16), nullable=False),
        sa.Column("excerpt_hash", sa.String(71), nullable=False),
        sa.Column("source_authority", sa.String(128)),
        sa.Column("screenshot_ref", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(24), nullable=False, server_default="ACCEPTED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["relation_candidate_id"], ["candidate_relations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["source_anchor_id"], ["source_anchors.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "(claim_id IS NULL) <> (relation_candidate_id IS NULL)",
            name="ck_evidence_records_target",
        ),
        sa.CheckConstraint(
            "stance IN ('SUPPORTS','OPPOSES','CONTEXT')", name="ck_evidence_records_stance"
        ),
        sa.CheckConstraint(f"excerpt_hash ~ '{CHECKSUM}'", name="ck_evidence_records_excerpt"),
        sa.CheckConstraint(
            "status IN ('ACCEPTED','REJECTED','STALE')", name="ck_evidence_records_status"
        ),
    )
    op.create_table(
        "conflict_cases",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("cluster_key", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(24), nullable=False, server_default="OPEN"),
        sa.Column("suggested_action", sa.String(64)),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID),
        _scope_fk(),
        sa.UniqueConstraint("space_id", "cluster_key", name="uq_conflict_cases_cluster"),
        sa.CheckConstraint(
            "severity IN ('INFO','WARNING','ERROR','BLOCKING')", name="ck_conflict_cases_severity"
        ),
        sa.CheckConstraint(
            "status IN ('OPEN','RESOLVED','UNRESOLVED','EXPIRED')", name="ck_conflict_cases_status"
        ),
    )
    op.create_table(
        "conflict_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("conflict_case_id", UUID, nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("object_type", sa.String(64), nullable=False),
        sa.Column("object_id", UUID, nullable=False),
        sa.Column(
            "evidence_snapshot", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.ForeignKeyConstraint(["conflict_case_id"], ["conflict_cases.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "conflict_case_id", "object_type", "object_id", name="uq_conflict_items_object"
        ),
        sa.CheckConstraint("side IN ('A','B','CONTEXT')", name="ck_conflict_items_side"),
    )
    op.create_table(
        "conflict_decisions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("conflict_case_id", UUID, nullable=False),
        sa.Column("resolution", sa.String(24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("conditions", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("comparison_snapshot", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(["conflict_case_id"], ["conflict_cases.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "resolution IN ('RETAIN_BOTH','CONDITIONAL','MERGE','UNRESOLVED','EXPIRED','REOPEN')",
            name="ck_conflict_decisions_resolution",
        ),
    )
    op.create_table(
        "review_cases",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("workflow_task_id", UUID, nullable=False),
        sa.Column("policy_id", UUID, nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", UUID, nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="OPEN"),
        sa.Column("current_stage", sa.String(24)),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(["workflow_task_id"], ["workflow_tasks.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["policy_id"], ["review_policies.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("space_id", "target_type", "target_id", name="uq_review_cases_target"),
        sa.CheckConstraint(
            "target_type IN ('CLAIM_CANDIDATE','RELATION_CANDIDATE','SEMANTIC_PROPOSAL')",
            name="ck_review_cases_target",
        ),
        sa.CheckConstraint("risk_level IN ('LOW','MEDIUM','HIGH')", name="ck_review_cases_risk"),
        sa.CheckConstraint(
            "status IN ('OPEN','WAITING_EVIDENCE','APPROVED','REJECTED','CANCELLED','OVERDUE')",
            name="ck_review_cases_status",
        ),
    )
    op.create_table(
        "review_tasks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("review_case_id", UUID, nullable=False),
        sa.Column("stage", sa.String(24), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("assignee_id", UUID),
        sa.Column("claimed_by", UUID),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("escalation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.ForeignKeyConstraint(["review_case_id"], ["review_cases.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("review_case_id", "stage", name="uq_review_tasks_stage"),
        sa.CheckConstraint(
            "stage IN ('ENGINEERING','EXPERT','APPROVAL')", name="ck_review_tasks_stage"
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','CLAIMED','WAITING_EVIDENCE','APPROVED','REJECTED','ESCALATED','CANCELLED')",
            name="ck_review_tasks_status",
        ),
    )
    op.create_table(
        "review_actions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("review_case_id", UUID, nullable=False),
        sa.Column("review_task_id", UUID, nullable=False),
        sa.Column("decision", sa.String(24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("change_set", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("before_snapshot", JSONB, nullable=False),
        sa.Column("after_snapshot", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(["review_case_id"], ["review_cases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["review_task_id"], ["review_tasks.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "decision IN ('ACCEPT','MODIFY','REJECT','REQUEST_EVIDENCE','TRANSFER')",
            name="ck_review_actions_decision",
        ),
    )
    for table in (
        "claims",
        "evidence_records",
        "conflict_items",
        "conflict_decisions",
        "review_actions",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_m6_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION nexweave_m5_immutable_guard()"
        )


def downgrade() -> None:
    for table in (
        "claims",
        "evidence_records",
        "conflict_items",
        "conflict_decisions",
        "review_actions",
    ):
        op.execute(f"DROP TRIGGER {table}_m6_immutable ON {table}")
    for table in (
        "review_actions",
        "review_tasks",
        "review_cases",
        "conflict_decisions",
        "conflict_items",
        "conflict_cases",
        "evidence_records",
        "claims",
        "review_policies",
    ):
        op.drop_table(table)
