"""Add M7 quality, immutable Release, projections, graph and trusted queries.

Revision ID: 0008_m7
Revises: 0007_m6
Create Date: 2026-08-31
"""
# ruff: noqa: E501

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_m7"
down_revision: str | None = "0007_m6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
UTC_NOW = sa.text("CURRENT_TIMESTAMP")
CHECKSUM = r"^sha256:[0-9a-f]{64}$"


class Vector16(sa.types.UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **_: object) -> str:
        return "vector(16)"


def _scope_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", "space_id"],
        ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "relations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("candidate_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("relation_type_key", sa.String(126), nullable=False),
        sa.Column("source_entity_id", UUID, nullable=False),
        sa.Column("target_entity_id", UUID, nullable=False),
        sa.Column("is_causal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(24), nullable=False, server_default="APPROVED"),
        sa.Column("provenance", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidate_relations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "source_entity_id"],
            [
                "knowledge_entities.tenant_id",
                "knowledge_entities.space_id",
                "knowledge_entities.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "target_entity_id"],
            [
                "knowledge_entities.tenant_id",
                "knowledge_entities.space_id",
                "knowledge_entities.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("candidate_id", name="uq_relations_candidate"),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_relations_scope_id"),
        sa.CheckConstraint(
            "status IN ('APPROVED','SUPERSEDED','REJECTED')", name="ck_relations_status"
        ),
        sa.CheckConstraint("source_entity_id <> target_entity_id", name="ck_relations_no_self"),
    )
    op.add_column("evidence_records", sa.Column("relation_id", UUID))
    op.create_foreign_key(
        "fk_evidence_records_relation",
        "evidence_records",
        "relations",
        ["relation_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("ck_evidence_records_target", "evidence_records", type_="check")
    op.create_check_constraint(
        "ck_evidence_records_target",
        "evidence_records",
        "num_nonnulls(claim_id, relation_id, relation_candidate_id) = 1",
    )

    op.add_column(
        "evaluation_suites", sa.Column("version", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column(
        "evaluation_suites",
        sa.Column("name", sa.String(255), nullable=False, server_default="Evaluation Suite"),
    )
    op.add_column(
        "evaluation_suites",
        sa.Column("minimum_pass_rate", sa.Integer(), nullable=False, server_default="100"),
    )
    op.add_column(
        "evaluation_suites",
        sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
    )
    op.add_column(
        "evaluation_suites",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
    )
    op.add_column("evaluation_suites", sa.Column("created_by", UUID))
    op.execute(
        "UPDATE evaluation_suites es SET created_by=sv.created_by FROM schema_versions sv WHERE sv.id=es.schema_version_id AND es.created_by IS NULL"
    )
    op.alter_column("evaluation_suites", "created_by", nullable=False)
    op.create_check_constraint(
        "ck_evaluation_suites_rate", "evaluation_suites", "minimum_pass_rate BETWEEN 0 AND 100"
    )
    op.create_check_constraint(
        "ck_evaluation_suites_status",
        "evaluation_suites",
        "status IN ('DRAFT','ACTIVE','DEPRECATED')",
    )
    op.create_table(
        "evaluation_cases",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("suite_id", UUID, nullable=False),
        sa.Column("case_key", sa.String(127), nullable=False),
        sa.Column("case_type", sa.String(32), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "expected_claim_ids", postgresql.ARRAY(UUID), nullable=False, server_default="{}"
        ),
        sa.Column(
            "expected_terms", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"
        ),
        sa.Column("expect_refusal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.ForeignKeyConstraint(["suite_id"], ["evaluation_suites.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("suite_id", "case_key", name="uq_evaluation_cases_key"),
        sa.CheckConstraint(
            "case_type IN ('ANSWERABLE','UNANSWERABLE','COUNTERFACTUAL','CONFLICT','MULTI_SOURCE','INSUFFICIENT_EVIDENCE')",
            name="ck_evaluation_cases_type",
        ),
    )
    op.create_table(
        "release_candidates",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("composition_checksum", sa.String(71), nullable=False),
        sa.Column("prompt_version_id", UUID, nullable=False),
        sa.Column("model_profile_id", UUID, nullable=False),
        sa.Column("evaluation_suite_id", UUID, nullable=False),
        sa.Column("workflow_task_id", UUID, nullable=False),
        sa.Column("workflow_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("manifest", JSONB, nullable=False),
        sa.Column("manifest_checksum", sa.String(71), nullable=False),
        sa.Column("gate_summary", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("index_config", JSONB, nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_suite_id"], ["evaluation_suites.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["workflow_task_id"], ["workflow_tasks.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("space_id", "version", name="uq_release_candidates_version"),
        sa.UniqueConstraint("workflow_id", name="uq_release_candidates_workflow"),
        sa.CheckConstraint(
            f"composition_checksum ~ '{CHECKSUM}'", name="ck_release_candidates_composition"
        ),
        sa.CheckConstraint(
            f"manifest_checksum ~ '{CHECKSUM}'", name="ck_release_candidates_manifest"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','VALIDATING','PENDING_APPROVAL','APPROVED','REJECTED','PUBLISHING','PUBLISHED','FAILED')",
            name="ck_release_candidates_status",
        ),
    )
    op.create_table(
        "release_candidate_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("candidate_id", UUID, nullable=False),
        sa.Column("object_type", sa.String(32), nullable=False),
        sa.Column("object_id", UUID, nullable=False),
        sa.Column("object_checksum", sa.String(71)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.ForeignKeyConstraint(["candidate_id"], ["release_candidates.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "candidate_id", "object_type", "object_id", name="uq_release_candidate_items_object"
        ),
        sa.CheckConstraint(
            "object_type IN ('CLAIM','RELATION','WIKI_PAGE_VERSION')",
            name="ck_release_candidate_items_type",
        ),
    )
    op.create_table(
        "evaluation_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("suite_id", UUID, nullable=False),
        sa.Column("suite_version", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", UUID, nullable=False),
        sa.Column("workflow_task_id", UUID),
        sa.Column("workflow_id", sa.String(255)),
        sa.Column("retrieval_strategy", sa.String(16), nullable=False),
        sa.Column("retrieval_config", JSONB, nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="CREATED"),
        sa.Column("metrics", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("gate_passed", sa.Boolean()),
        sa.Column("error_code", sa.String(128)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(["suite_id"], ["evaluation_suites.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workflow_task_id"], ["workflow_tasks.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "target_type IN ('RELEASE_CANDIDATE','RELEASE')", name="ck_evaluation_runs_target"
        ),
        sa.CheckConstraint(
            "retrieval_strategy IN ('KEYWORD','ATTRIBUTE','SEMANTIC','HYBRID')",
            name="ck_evaluation_runs_strategy",
        ),
        sa.CheckConstraint(
            "status IN ('CREATED','RUNNING','SUCCEEDED','FAILED','CANCELED')",
            name="ck_evaluation_runs_status",
        ),
    )
    op.create_table(
        "evaluation_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("case_id", UUID, nullable=False),
        sa.Column("case_key", sa.String(127), nullable=False),
        sa.Column("case_type", sa.String(32), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("answer_status", sa.String(24), nullable=False),
        sa.Column("matched_claim_ids", postgresql.ARRAY(UUID), nullable=False, server_default="{}"),
        sa.Column("error_code", sa.String(128)),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["case_id"], ["evaluation_cases.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("run_id", "case_id", name="uq_evaluation_results_case"),
    )
    op.create_table(
        "release_lint_findings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("candidate_id", UUID, nullable=False),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("blocking", sa.Boolean(), nullable=False),
        sa.Column("object_type", sa.String(32), nullable=False),
        sa.Column("object_id", UUID),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        _scope_fk(),
        sa.ForeignKeyConstraint(["candidate_id"], ["release_candidates.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "candidate_id",
            "code",
            "object_type",
            "object_id",
            name="uq_release_lint_findings_identity",
        ),
        sa.CheckConstraint(
            "severity IN ('INFO','WARNING','ERROR','BLOCKING')",
            name="ck_release_lint_findings_severity",
        ),
    )
    op.create_table(
        "release_approvals",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("candidate_id", UUID, nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["release_candidates.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "decision IN ('APPROVED','REJECTED')", name="ck_release_approvals_decision"
        ),
    )
    op.create_table(
        "releases",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("candidate_id", UUID, nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="PUBLISHED"),
        sa.Column("manifest", JSONB, nullable=False),
        sa.Column("manifest_checksum", sa.String(71), nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("composition_checksum", sa.String(71), nullable=False),
        sa.Column("prompt_version_id", UUID, nullable=False),
        sa.Column("model_profile_id", UUID, nullable=False),
        sa.Column("index_config", JSONB, nullable=False),
        sa.Column(
            "published_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW
        ),
        sa.Column("published_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(["candidate_id"], ["release_candidates.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("candidate_id", name="uq_releases_candidate"),
        sa.UniqueConstraint("space_id", "version", name="uq_releases_version"),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_releases_scope_id"),
        sa.CheckConstraint("status = 'PUBLISHED'", name="ck_releases_status"),
        sa.CheckConstraint(f"manifest_checksum ~ '{CHECKSUM}'", name="ck_releases_manifest"),
        sa.CheckConstraint(f"composition_checksum ~ '{CHECKSUM}'", name="ck_releases_composition"),
    )
    op.create_table(
        "release_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("release_id", UUID, nullable=False),
        sa.Column("object_type", sa.String(32), nullable=False),
        sa.Column("object_id", UUID, nullable=False),
        sa.Column("object_checksum", sa.String(71)),
        sa.Column("snapshot", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "release_id"],
            ["releases.tenant_id", "releases.space_id", "releases.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "release_id", "object_type", "object_id", name="uq_release_items_object"
        ),
        sa.CheckConstraint(
            "object_type IN ('CLAIM','EVIDENCE','RELATION','ENTITY','WIKI_PAGE_VERSION')",
            name="ck_release_items_type",
        ),
    )
    op.create_table(
        "release_pointers",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("release_id", UUID, nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "release_id"],
            ["releases.tenant_id", "releases.space_id", "releases.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("space_id", "channel", name="uq_release_pointers_channel"),
    )
    op.create_table(
        "release_pointer_history",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("pointer_id", UUID, nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("old_release_id", UUID),
        sa.Column("new_release_id", UUID, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("pointer_version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(["pointer_id"], ["release_pointers.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "release_deprecations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("release_id", UUID, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("replacement_release_id", UUID),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(["release_id"], ["releases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["replacement_release_id"], ["releases.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("release_id", name="uq_release_deprecations_release"),
    )
    op.create_table(
        "release_search_documents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("release_id", UUID, nullable=False),
        sa.Column("object_type", sa.String(32), nullable=False),
        sa.Column("object_id", UUID, nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("attributes", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=False),
        sa.Column("embedding", Vector16(), nullable=False),
        sa.Column("projection_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "release_id"],
            ["releases.tenant_id", "releases.space_id", "releases.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "release_id", "object_type", "object_id", name="uq_release_search_documents_object"
        ),
    )
    op.create_index(
        "ix_release_search_documents_fts",
        "release_search_documents",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_release_search_documents_vector",
        "release_search_documents",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_table(
        "query_sessions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("release_id", UUID, nullable=False),
        sa.Column("client_request_id", sa.String(128), nullable=False),
        sa.Column("policy_snapshot", JSONB, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="CLOSED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "release_id"],
            ["releases.tenant_id", "releases.space_id", "releases.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "tenant_id", "created_by", "client_request_id", name="uq_query_sessions_client"
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE','CLOSED','EXPIRED')", name="ck_query_sessions_status"
        ),
    )
    op.create_table(
        "query_answers",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("query_session_id", UUID, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("release_id", UUID, nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("direct_answer", sa.Text(), nullable=False),
        sa.Column("key_basis", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("uncertainty", sa.Text()),
        sa.Column("conflicts", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("retrieval_strategy", sa.String(16), nullable=False),
        sa.Column("retrieval_config", JSONB, nullable=False),
        sa.Column("model_profile_id", UUID, nullable=False),
        sa.Column("prompt_version_id", UUID, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.ForeignKeyConstraint(["query_session_id"], ["query_sessions.id"], ondelete="RESTRICT"),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "release_id"],
            ["releases.tenant_id", "releases.space_id", "releases.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('COMPLETED','REFUSED','FAILED')", name="ck_query_answers_status"
        ),
    )
    op.create_table(
        "citations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("answer_id", UUID, nullable=False),
        sa.Column("release_id", UUID, nullable=False),
        sa.Column("evidence_id", UUID, nullable=False),
        sa.Column("source_version_id", UUID, nullable=False),
        sa.Column("source_anchor_id", UUID, nullable=False),
        sa.Column("claim_id", UUID),
        sa.Column("relation_id", UUID),
        sa.Column("excerpt", sa.Text()),
        sa.Column("locator", JSONB, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="VALID"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        _scope_fk(),
        sa.ForeignKeyConstraint(["answer_id"], ["query_answers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["release_id"], ["releases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_records.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_version_id"], ["source_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_anchor_id"], ["source_anchors.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "(claim_id IS NULL) <> (relation_id IS NULL)", name="ck_citations_target"
        ),
        sa.CheckConstraint("status IN ('VALID','INVALID')", name="ck_citations_status"),
        sa.UniqueConstraint("answer_id", "evidence_id", name="uq_citations_evidence"),
    )
    immutable = (
        "relations",
        "evaluation_cases",
        "evaluation_results",
        "release_lint_findings",
        "release_candidate_items",
        "release_approvals",
        "releases",
        "release_items",
        "release_pointer_history",
        "release_deprecations",
        "query_sessions",
        "query_answers",
        "citations",
    )
    for table in immutable:
        op.execute(
            f"CREATE TRIGGER {table}_m7_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION nexweave_m5_immutable_guard()"
        )


def downgrade() -> None:
    immutable = (
        "relations",
        "evaluation_cases",
        "evaluation_results",
        "release_lint_findings",
        "release_candidate_items",
        "release_approvals",
        "releases",
        "release_items",
        "release_pointer_history",
        "release_deprecations",
        "query_sessions",
        "query_answers",
        "citations",
    )
    for table in immutable:
        op.execute(f"DROP TRIGGER {table}_m7_immutable ON {table}")
    for table in (
        "citations",
        "query_answers",
        "query_sessions",
        "release_search_documents",
        "release_deprecations",
        "release_pointer_history",
        "release_pointers",
        "release_items",
        "releases",
        "release_approvals",
        "release_lint_findings",
        "evaluation_results",
        "evaluation_runs",
        "release_candidate_items",
        "release_candidates",
        "evaluation_cases",
    ):
        op.drop_table(table)
    op.drop_constraint("ck_evaluation_suites_status", "evaluation_suites", type_="check")
    op.drop_constraint("ck_evaluation_suites_rate", "evaluation_suites", type_="check")
    for column in ("created_by", "created_at", "status", "minimum_pass_rate", "name", "version"):
        op.drop_column("evaluation_suites", column)
    op.drop_constraint("ck_evidence_records_target", "evidence_records", type_="check")
    op.drop_constraint("fk_evidence_records_relation", "evidence_records", type_="foreignkey")
    op.drop_column("evidence_records", "relation_id")
    op.create_check_constraint(
        "ck_evidence_records_target",
        "evidence_records",
        "(claim_id IS NULL) <> (relation_candidate_id IS NULL)",
    )
    op.drop_table("relations")
