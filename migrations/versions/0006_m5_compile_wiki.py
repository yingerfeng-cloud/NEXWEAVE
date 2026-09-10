"""Add M5 governed Compile, candidate knowledge and Wiki draft facts.

Revision ID: 0006_m5
Revises: 0005_m4
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_m5"
down_revision: str | None = "0005_m4"
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


def _record_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "compile_jobs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("composition_checksum", sa.String(71), nullable=False),
        sa.Column("prompt_version_id", UUID, nullable=False),
        sa.Column("model_profile_id", UUID, nullable=False),
        sa.Column("workflow_task_id", UUID, nullable=False),
        sa.Column("workflow_id", sa.String(768), nullable=False),
        sa.Column("run_id", sa.String(255)),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="CREATED"),
        sa.Column("input_fingerprint", sa.String(71), nullable=False),
        sa.Column("normalization_version", sa.String(64), nullable=False),
        sa.Column("scope", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_summary", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result_summary", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_code", sa.String(128)),
        sa.Column("error_detail", sa.String(1024)),
        *_record_columns(),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "prompt_version_id"],
            ["prompt_versions.tenant_id", "prompt_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "model_profile_id"],
            ["model_profiles.tenant_id", "model_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "workflow_task_id"],
            ["workflow_tasks.tenant_id", "workflow_tasks.space_id", "workflow_tasks.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_compile_jobs_scope_id"),
        sa.UniqueConstraint("workflow_task_id", name="uq_compile_jobs_workflow_task"),
        sa.CheckConstraint(
            f"composition_checksum ~ '{CHECKSUM}'", name="ck_compile_jobs_composition"
        ),
        sa.CheckConstraint(f"input_fingerprint ~ '{CHECKSUM}'", name="ck_compile_jobs_fingerprint"),
        sa.CheckConstraint(
            "mode IN ('FULL','INCREMENTAL','SOURCE_SCOPED','RECOMPILE')",
            name="ck_compile_jobs_mode",
        ),
        sa.CheckConstraint(
            "status IN ('CREATED','QUEUED','RUNNING','PAUSED','PARTIAL_FAILED','FAILED','SUCCEEDED','CANCELED')",
            name="ck_compile_jobs_status",
        ),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name="ck_compile_jobs_progress"),
    )
    op.create_index(
        "ix_compile_jobs_scope_created",
        "compile_jobs",
        ["tenant_id", "space_id", "created_at", "id"],
    )

    op.create_table(
        "compile_job_sources",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("compile_job_id", UUID, nullable=False),
        sa.Column("source_version_id", UUID, nullable=False),
        sa.Column("source_checksum", sa.String(71), nullable=False),
        sa.Column("parse_job_id", UUID, nullable=False),
        sa.Column("input_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "compile_job_id"],
            ["compile_jobs.tenant_id", "compile_jobs.space_id", "compile_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "source_version_id"],
            ["source_versions.tenant_id", "source_versions.space_id", "source_versions.id"],
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
        sa.UniqueConstraint(
            "compile_job_id", "source_version_id", name="uq_compile_job_sources_version"
        ),
        sa.UniqueConstraint("compile_job_id", "input_order", name="uq_compile_job_sources_order"),
        sa.CheckConstraint(
            f"source_checksum ~ '{CHECKSUM}'", name="ck_compile_job_sources_checksum"
        ),
    )

    op.create_table(
        "compile_steps",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("compile_job_id", UUID, nullable=False),
        sa.Column("step_key", sa.String(128), nullable=False),
        sa.Column("input_checksum", sa.String(71), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("output_summary", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_code", sa.String(128)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "compile_job_id"],
            ["compile_jobs.tenant_id", "compile_jobs.space_id", "compile_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "compile_job_id", "step_key", "input_checksum", name="uq_compile_steps_idempotency"
        ),
        sa.CheckConstraint(f"input_checksum ~ '{CHECKSUM}'", name="ck_compile_steps_checksum"),
        sa.CheckConstraint(
            "status IN ('PENDING','RUNNING','RETRYING','FAILED','SUCCEEDED','SKIPPED')",
            name="ck_compile_steps_status",
        ),
        sa.CheckConstraint("attempt >= 1", name="ck_compile_steps_attempt"),
    )

    op.create_table(
        "model_invocations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("compile_job_id", UUID, nullable=False),
        sa.Column("compile_step_id", UUID),
        sa.Column("model_profile_id", UUID, nullable=False),
        sa.Column("prompt_version_id", UUID, nullable=False),
        sa.Column("capability", sa.String(32), nullable=False),
        sa.Column("provider_request_id", sa.String(255)),
        sa.Column("input_checksum", sa.String(71), nullable=False),
        sa.Column("output_checksum", sa.String(71)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("input_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_microunits", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "compile_job_id"],
            ["compile_jobs.tenant_id", "compile_jobs.space_id", "compile_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["compile_step_id"], ["compile_steps.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "model_profile_id"],
            ["model_profiles.tenant_id", "model_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "prompt_version_id"],
            ["prompt_versions.tenant_id", "prompt_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(f"input_checksum ~ '{CHECKSUM}'", name="ck_model_invocations_input"),
        sa.CheckConstraint(
            f"output_checksum IS NULL OR output_checksum ~ '{CHECKSUM}'",
            name="ck_model_invocations_output",
        ),
        sa.CheckConstraint(
            "capability IN ('STRUCTURED_OUTPUT','EMBEDDING')",
            name="ck_model_invocations_capability",
        ),
        sa.CheckConstraint(
            "status IN ('SUCCEEDED','FAILED','REJECTED')", name="ck_model_invocations_status"
        ),
    )

    op.create_table(
        "knowledge_entities",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("type_key", sa.String(126), nullable=False),
        sa.Column("normalized_key", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("current_version_id", UUID),
        *_record_columns(),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_knowledge_entities_scope_id"),
        sa.UniqueConstraint(
            "space_id",
            "schema_version_id",
            "type_key",
            "normalized_key",
            name="uq_knowledge_entities_identity",
        ),
        sa.CheckConstraint(f"type_key ~ '{STABLE_KEY}'", name="ck_knowledge_entities_type_key"),
        sa.CheckConstraint(
            "status IN ('DRAFT','NEEDS_MAPPING','IN_REVIEW','APPROVED','DEPRECATED')",
            name="ck_knowledge_entities_status",
        ),
    )
    op.create_table(
        "knowledge_entity_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("entity_id", UUID, nullable=False),
        sa.Column("compile_job_id", UUID, nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("attributes", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("aliases", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("provenance", JSONB, nullable=False),
        sa.Column("content_checksum", sa.String(71), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="AI_DRAFT"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "entity_id"],
            [
                "knowledge_entities.tenant_id",
                "knowledge_entities.space_id",
                "knowledge_entities.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "compile_job_id"],
            ["compile_jobs.tenant_id", "compile_jobs.space_id", "compile_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("entity_id", "revision", name="uq_entity_versions_revision"),
        sa.UniqueConstraint("entity_id", "content_checksum", name="uq_entity_versions_content"),
        sa.CheckConstraint(f"content_checksum ~ '{CHECKSUM}'", name="ck_entity_versions_checksum"),
        sa.CheckConstraint(
            "status IN ('AI_DRAFT','EDITING','PENDING_REVIEW','APPROVED','REJECTED')",
            name="ck_entity_versions_status",
        ),
    )

    op.create_table(
        "wiki_pages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("primary_entity_id", UUID, nullable=False),
        sa.Column("template_key", sa.String(126), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("current_version_id", UUID),
        *_record_columns(),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "primary_entity_id"],
            [
                "knowledge_entities.tenant_id",
                "knowledge_entities.space_id",
                "knowledge_entities.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_wiki_pages_scope_id"),
        sa.UniqueConstraint(
            "space_id", "primary_entity_id", "template_key", name="uq_wiki_pages_identity"
        ),
        sa.UniqueConstraint("space_id", "slug", name="uq_wiki_pages_slug"),
        sa.CheckConstraint(f"template_key ~ '{STABLE_KEY}'", name="ck_wiki_pages_template_key"),
        sa.CheckConstraint(
            "status IN ('DRAFT','IN_REVIEW','APPROVED','DEPRECATED')", name="ck_wiki_pages_status"
        ),
    )
    op.create_table(
        "wiki_page_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("wiki_page_id", UUID, nullable=False),
        sa.Column("compile_job_id", UUID),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "generated_sections", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "protected_sections", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("properties", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("content_checksum", sa.String(71), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("edit_reason", sa.String(1024)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "wiki_page_id"],
            ["wiki_pages.tenant_id", "wiki_pages.space_id", "wiki_pages.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "compile_job_id"],
            ["compile_jobs.tenant_id", "compile_jobs.space_id", "compile_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("wiki_page_id", "revision", name="uq_wiki_page_versions_revision"),
        sa.UniqueConstraint(
            "wiki_page_id", "content_checksum", name="uq_wiki_page_versions_content"
        ),
        sa.CheckConstraint(
            f"content_checksum ~ '{CHECKSUM}'", name="ck_wiki_page_versions_checksum"
        ),
        sa.CheckConstraint(
            "status IN ('AI_DRAFT','EDITING','PENDING_REVIEW','APPROVED','REJECTED')",
            name="ck_wiki_page_versions_status",
        ),
    )

    op.create_table(
        "candidate_relations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("compile_job_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("relation_type_key", sa.String(126), nullable=False),
        sa.Column("source_entity_id", UUID, nullable=False),
        sa.Column("target_entity_id", UUID, nullable=False),
        sa.Column("source_anchor_id", UUID),
        sa.Column("status", sa.String(32), nullable=False, server_default="CANDIDATE"),
        sa.Column("confidence", sa.Numeric(5, 4)),
        sa.Column("provenance", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "compile_job_id"],
            ["compile_jobs.tenant_id", "compile_jobs.space_id", "compile_jobs.id"],
            ondelete="RESTRICT",
        ),
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
        sa.ForeignKeyConstraint(["source_anchor_id"], ["source_anchors.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "compile_job_id",
            "relation_type_key",
            "source_entity_id",
            "target_entity_id",
            "source_anchor_id",
            name="uq_candidate_relations_identity",
        ),
        sa.CheckConstraint(
            f"relation_type_key ~ '{STABLE_KEY}'", name="ck_candidate_relations_key"
        ),
        sa.CheckConstraint(
            "status IN ('CANDIDATE','NEEDS_EVIDENCE','NEEDS_MAPPING','REJECTED')",
            name="ck_candidate_relations_status",
        ),
    )

    op.create_table(
        "claim_candidates",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("compile_job_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("subject_entity_id", UUID, nullable=False),
        sa.Column("predicate_key", sa.String(126), nullable=False),
        sa.Column("object_value", JSONB, nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="CANDIDATE"),
        sa.Column("provenance", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "compile_job_id"],
            ["compile_jobs.tenant_id", "compile_jobs.space_id", "compile_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "subject_entity_id"],
            [
                "knowledge_entities.tenant_id",
                "knowledge_entities.space_id",
                "knowledge_entities.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "compile_job_id",
            "subject_entity_id",
            "predicate_key",
            "statement",
            name="uq_claim_candidates_identity",
        ),
        sa.CheckConstraint(f"predicate_key ~ '{STABLE_KEY}'", name="ck_claim_candidates_predicate"),
        sa.CheckConstraint(
            "status IN ('CANDIDATE','NEEDS_EVIDENCE','NEEDS_MAPPING','REJECTED')",
            name="ck_claim_candidates_status",
        ),
    )

    op.create_table(
        "evidence_candidates",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("compile_job_id", UUID, nullable=False),
        sa.Column("claim_candidate_id", UUID),
        sa.Column("relation_candidate_id", UUID),
        sa.Column("source_anchor_id", UUID, nullable=False),
        sa.Column("stance", sa.String(16), nullable=False, server_default="SUPPORTS"),
        sa.Column("excerpt_hash", sa.String(71), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="CANDIDATE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "compile_job_id"],
            ["compile_jobs.tenant_id", "compile_jobs.space_id", "compile_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["claim_candidate_id"], ["claim_candidates.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["relation_candidate_id"], ["candidate_relations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["source_anchor_id"], ["source_anchors.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "compile_job_id",
            "claim_candidate_id",
            "relation_candidate_id",
            "source_anchor_id",
            name="uq_evidence_candidates_identity",
        ),
        sa.CheckConstraint(f"excerpt_hash ~ '{CHECKSUM}'", name="ck_evidence_candidates_excerpt"),
        sa.CheckConstraint(
            "(claim_candidate_id IS NULL) <> (relation_candidate_id IS NULL)",
            name="ck_evidence_candidates_target",
        ),
        sa.CheckConstraint(
            "stance IN ('SUPPORTS','OPPOSES','CONTEXT')", name="ck_evidence_candidates_stance"
        ),
    )

    op.create_table(
        "semantic_change_proposals",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("compile_job_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("proposal_kind", sa.String(32), nullable=False),
        sa.Column("candidate_key", sa.String(126)),
        sa.Column("term", sa.String(512), nullable=False),
        sa.Column("proposal", JSONB, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="CANDIDATE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "compile_job_id"],
            ["compile_jobs.tenant_id", "compile_jobs.space_id", "compile_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "compile_job_id", "proposal_kind", "term", name="uq_semantic_change_proposals_identity"
        ),
        sa.CheckConstraint(
            "proposal_kind IN ('TYPE','TERM','MAPPING','PROPERTY','RELATION')",
            name="ck_semantic_change_proposals_kind",
        ),
        sa.CheckConstraint(
            "status IN ('CANDIDATE','PENDING_REVIEW','ACCEPTED','REJECTED')",
            name="ck_semantic_change_proposals_status",
        ),
    )

    op.create_table(
        "wiki_page_links",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("source_page_id", UUID, nullable=False),
        sa.Column("target_page_id", UUID, nullable=False),
        sa.Column("link_kind", sa.String(32), nullable=False, server_default="WIKI"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "source_page_id"],
            ["wiki_pages.tenant_id", "wiki_pages.space_id", "wiki_pages.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "target_page_id"],
            ["wiki_pages.tenant_id", "wiki_pages.space_id", "wiki_pages.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "source_page_id", "target_page_id", "link_kind", name="uq_wiki_page_links_identity"
        ),
        sa.CheckConstraint("source_page_id <> target_page_id", name="ck_wiki_page_links_no_self"),
    )
    op.create_table(
        "wiki_page_comments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("wiki_page_id", UUID, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "wiki_page_id"],
            ["wiki_pages.tenant_id", "wiki_pages.space_id", "wiki_pages.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("status IN ('OPEN','RESOLVED')", name="ck_wiki_page_comments_status"),
    )
    op.create_table(
        "wiki_page_follows",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("wiki_page_id", UUID, nullable=False),
        sa.Column("actor_id", UUID, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "wiki_page_id"],
            ["wiki_pages.tenant_id", "wiki_pages.space_id", "wiki_pages.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("wiki_page_id", "actor_id", name="uq_wiki_page_follows_actor"),
    )

    for table in ("conflict_candidates", "lint_findings"):
        op.create_table(
            table,
            sa.Column("id", UUID, primary_key=True),
            sa.Column("tenant_id", UUID, nullable=False),
            sa.Column("space_id", UUID, nullable=False),
            sa.Column("compile_job_id", UUID, nullable=False),
            sa.Column("code", sa.String(128), nullable=False),
            sa.Column("severity", sa.String(16), nullable=False),
            sa.Column("object_type", sa.String(64), nullable=False),
            sa.Column("object_id", UUID),
            sa.Column("details", JSONB, nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW
            ),
            _scope_fk(),
            sa.ForeignKeyConstraint(
                ["tenant_id", "space_id", "compile_job_id"],
                ["compile_jobs.tenant_id", "compile_jobs.space_id", "compile_jobs.id"],
                ondelete="RESTRICT",
            ),
            sa.CheckConstraint(
                "severity IN ('INFO','WARNING','ERROR','BLOCKING')", name=f"ck_{table}_severity"
            ),
            sa.CheckConstraint(
                "status IN ('OPEN','ACKNOWLEDGED','RESOLVED')", name=f"ck_{table}_status"
            ),
        )

    op.execute("""
    CREATE FUNCTION nexweave_m5_immutable_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'M5 immutable fact cannot be updated or deleted';
    END; $$
    """)
    for table in (
        "compile_job_sources",
        "model_invocations",
        "knowledge_entity_versions",
        "wiki_page_versions",
        "evidence_candidates",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION nexweave_m5_immutable_guard()"
        )


def downgrade() -> None:
    for table in (
        "compile_job_sources",
        "model_invocations",
        "knowledge_entity_versions",
        "wiki_page_versions",
        "evidence_candidates",
    ):
        op.execute(f"DROP TRIGGER {table}_immutable ON {table}")
    op.execute("DROP FUNCTION nexweave_m5_immutable_guard()")
    for table in (
        "lint_findings",
        "conflict_candidates",
        "wiki_page_follows",
        "wiki_page_comments",
        "wiki_page_links",
        "semantic_change_proposals",
        "evidence_candidates",
        "claim_candidates",
        "candidate_relations",
        "wiki_page_versions",
        "wiki_pages",
        "knowledge_entity_versions",
        "knowledge_entities",
        "model_invocations",
        "compile_steps",
        "compile_job_sources",
    ):
        op.drop_table(table)
    op.drop_index("ix_compile_jobs_scope_created", table_name="compile_jobs")
    op.drop_table("compile_jobs")
