"""Add M4 immutable semantic model, Pack registry and installation facts.

Revision ID: 0005_m4
Revises: 0004_m3
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_m4"
down_revision: str | None = "0004_m3"
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
        "schema_definitions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_key", sa.String(126), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        *_record_columns(),
        _scope_fk(),
        sa.UniqueConstraint(
            "tenant_id", "space_id", "schema_key", name="uq_schema_definitions_key"
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_schema_definitions_scope_id"),
        sa.CheckConstraint(f"schema_key ~ '{STABLE_KEY}'", name="ck_schema_definitions_key"),
        sa.CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_schema_definitions_status"),
    )
    op.create_table(
        "schema_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_definition_id", UUID, nullable=False),
        sa.Column("semantic_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column(
            "local_declarations", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("normalized_snapshot", JSONB, nullable=False),
        sa.Column("content_checksum", sa.String(71), nullable=False),
        sa.Column("composition_checksum", sa.String(71), nullable=False),
        sa.Column("canonicalization_algorithm", sa.String(64), nullable=False),
        sa.Column("breaking_change", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("published_by", UUID),
        *_record_columns(),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_definition_id"],
            [
                "schema_definitions.tenant_id",
                "schema_definitions.space_id",
                "schema_definitions.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_schema_versions_scope_id"),
        sa.UniqueConstraint(
            "schema_definition_id", "semantic_version", name="uq_schema_versions_semver"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','TESTING','PUBLISHED','DEPRECATED')",
            name="ck_schema_versions_status",
        ),
        sa.CheckConstraint(
            f"content_checksum ~ '{CHECKSUM}'", name="ck_schema_versions_content_checksum"
        ),
        sa.CheckConstraint(
            f"composition_checksum ~ '{CHECKSUM}'", name="ck_schema_versions_composition_checksum"
        ),
    )
    for table, key_column, extra in (
        (
            "entity_types",
            "type_key",
            [
                sa.Column("display_name", sa.String(255), nullable=False),
                sa.Column("definition", JSONB, nullable=False),
            ],
        ),
        ("relation_types", "relation_type_key", [sa.Column("definition", JSONB, nullable=False)]),
    ):
        op.create_table(
            table,
            sa.Column("id", UUID, primary_key=True),
            sa.Column("tenant_id", UUID, nullable=False),
            sa.Column("space_id", UUID, nullable=False),
            sa.Column("schema_version_id", UUID, nullable=False),
            sa.Column(key_column, sa.String(126), nullable=False),
            *extra,
            _scope_fk(),
            sa.ForeignKeyConstraint(
                ["tenant_id", "space_id", "schema_version_id"],
                ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
                ondelete="RESTRICT",
            ),
            sa.UniqueConstraint("schema_version_id", key_column, name=f"uq_{table}_version_key"),
            sa.UniqueConstraint(
                "tenant_id",
                "space_id",
                "schema_version_id",
                "id",
                name=f"uq_{table}_scope_id",
            ),
            sa.CheckConstraint(f"{key_column} ~ '{STABLE_KEY}'", name=f"ck_{table}_key"),
        )
    op.create_table(
        "property_definitions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("entity_type_id", UUID, nullable=False),
        sa.Column("property_key", sa.String(126), nullable=False),
        sa.Column("definition", JSONB, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id", "entity_type_id"],
            [
                "entity_types.tenant_id",
                "entity_types.space_id",
                "entity_types.schema_version_id",
                "entity_types.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "entity_type_id", "property_key", name="uq_property_definitions_type_key"
        ),
        sa.CheckConstraint(f"property_key ~ '{STABLE_KEY}'", name="ck_property_definitions_key"),
    )
    op.create_table(
        "type_hierarchy_edges",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("child_type_key", sa.String(126), nullable=False),
        sa.Column("parent_type_key", sa.String(126), nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "schema_version_id",
            "child_type_key",
            "parent_type_key",
            name="uq_type_hierarchy_edges_pair",
        ),
        sa.CheckConstraint(
            f"child_type_key ~ '{STABLE_KEY}' AND parent_type_key ~ '{STABLE_KEY}' AND child_type_key <> parent_type_key",
            name="ck_type_hierarchy_edges_keys",
        ),
    )
    op.create_table(
        "type_terms",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("target_key", sa.String(126), nullable=False),
        sa.Column("language", sa.String(35), nullable=False),
        sa.Column("term", sa.String(512), nullable=False),
        sa.Column("term_kind", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(128), nullable=False, server_default="GLOBAL"),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "schema_version_id",
            "target_key",
            "language",
            "term",
            "scope",
            name="uq_type_terms_identity",
        ),
        sa.CheckConstraint(f"target_key ~ '{STABLE_KEY}'", name="ck_type_terms_target_key"),
        sa.CheckConstraint(
            "term_kind IN ('PREFERRED','ALIAS','ABBREVIATION')", name="ck_type_terms_kind"
        ),
    )
    op.create_table(
        "concept_mappings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("source_key", sa.String(126), nullable=False),
        sa.Column("target_key", sa.String(126), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("approval_status", sa.String(32), nullable=False, server_default="PENDING"),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "schema_version_id",
            "source_key",
            "target_key",
            "kind",
            name="uq_concept_mappings_identity",
        ),
        sa.CheckConstraint(
            f"source_key ~ '{STABLE_KEY}' AND target_key ~ '{STABLE_KEY}'",
            name="ck_concept_mappings_keys",
        ),
        sa.CheckConstraint(
            "kind IN ('EXACT','BROADER','NARROWER','RELATED')", name="ck_concept_mappings_kind"
        ),
    )
    for table, key_column in (
        ("page_templates", "template_key"),
        ("lint_rules", "rule_key"),
        ("evaluation_suites", "suite_key"),
        ("ui_declarations", "ui_key"),
    ):
        op.create_table(
            table,
            sa.Column("id", UUID, primary_key=True),
            sa.Column("tenant_id", UUID, nullable=False),
            sa.Column("space_id", UUID, nullable=False),
            sa.Column("schema_version_id", UUID, nullable=False),
            sa.Column(key_column, sa.String(126), nullable=False),
            sa.Column("definition", JSONB, nullable=False),
            _scope_fk(),
            sa.ForeignKeyConstraint(
                ["tenant_id", "space_id", "schema_version_id"],
                ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
                ondelete="RESTRICT",
            ),
            sa.UniqueConstraint("schema_version_id", key_column, name=f"uq_{table}_version_key"),
            sa.CheckConstraint(f"{key_column} ~ '{STABLE_KEY}'", name=f"ck_{table}_key"),
        )
    op.create_table(
        "schema_migration_plans",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("from_checksum", sa.String(71), nullable=False),
        sa.Column("to_checksum", sa.String(71), nullable=False),
        sa.Column("dsl_version", sa.String(64), nullable=False),
        sa.Column("operations", JSONB, nullable=False),
        sa.Column("rollback_operations", JSONB, nullable=False),
        sa.Column("breaking", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PREVIEWED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "schema_version_id", "from_checksum", "to_checksum", name="uq_schema_migration_plans"
        ),
        sa.CheckConstraint(
            f"from_checksum ~ '{CHECKSUM}' AND to_checksum ~ '{CHECKSUM}'",
            name="ck_schema_migration_plans_checksums",
        ),
        sa.CheckConstraint(
            "status IN ('PREVIEWED','APPROVED','REJECTED')",
            name="ck_schema_migration_plans_status",
        ),
        sa.CheckConstraint(
            "jsonb_array_length(operations) <= 100 AND jsonb_array_length(rollback_operations) <= 100",
            name="ck_schema_migration_plans_budget",
        ),
    )
    op.create_table(
        "domain_packs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("pack_key", sa.String(63), nullable=False),
        sa.Column("publisher", sa.String(255), nullable=False),
        sa.Column("key_namespace", sa.String(63), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        *_record_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "pack_key", name="uq_domain_packs_key"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_domain_packs_tenant_id"),
        sa.CheckConstraint("status IN ('ACTIVE','DEPRECATED')", name="ck_domain_packs_status"),
    )
    op.create_table(
        "domain_pack_trust_keys",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("key_id", sa.String(128), nullable=False),
        sa.Column("key_namespace", sa.String(63), nullable=False),
        sa.Column("algorithm", sa.String(32), nullable=False, server_default="Ed25519"),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("fingerprint", sa.String(71), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        *_record_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "key_id", name="uq_domain_pack_trust_keys_key"),
        sa.CheckConstraint("algorithm = 'Ed25519'", name="ck_domain_pack_trust_keys_algorithm"),
        sa.CheckConstraint(
            "status IN ('ACTIVE','SUSPENDED','REVOKED')",
            name="ck_domain_pack_trust_keys_status",
        ),
        sa.CheckConstraint(
            f"fingerprint ~ '{CHECKSUM}'", name="ck_domain_pack_trust_keys_fingerprint"
        ),
    )
    op.create_table(
        "domain_pack_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("domain_pack_id", UUID, nullable=False),
        sa.Column("pack_version", sa.String(64), nullable=False),
        sa.Column("content_checksum", sa.String(71), nullable=False),
        sa.Column("manifest", JSONB, nullable=False),
        sa.Column("signature_key_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="VALIDATED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "domain_pack_id"],
            ["domain_packs.tenant_id", "domain_packs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "signature_key_id"],
            ["domain_pack_trust_keys.tenant_id", "domain_pack_trust_keys.key_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "domain_pack_id", "pack_version", name="uq_domain_pack_versions_version"
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_domain_pack_versions_tenant_id"),
        sa.CheckConstraint(
            f"content_checksum ~ '{CHECKSUM}'", name="ck_domain_pack_versions_checksum"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','VALIDATED','PUBLISHED','REVOKED','DEPRECATED')",
            name="ck_domain_pack_versions_status",
        ),
    )
    op.create_table(
        "domain_pack_contents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("domain_pack_version_id", UUID, nullable=False),
        sa.Column("content_key", sa.String(128), nullable=False),
        sa.Column("path", sa.String(192), nullable=False),
        sa.Column("checksum", sa.String(71), nullable=False),
        sa.Column("declaration", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "domain_pack_version_id"],
            ["domain_pack_versions.tenant_id", "domain_pack_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "domain_pack_version_id", "content_key", name="uq_domain_pack_contents_key"
        ),
        sa.UniqueConstraint("domain_pack_version_id", "path", name="uq_domain_pack_contents_path"),
        sa.CheckConstraint(f"checksum ~ '{CHECKSUM}'", name="ck_domain_pack_contents_checksum"),
        sa.CheckConstraint(
            "path !~ '(^/|(^|/)\\.\\.?(/|$)|//)'", name="ck_domain_pack_contents_safe_path"
        ),
    )
    op.create_table(
        "domain_pack_dependencies",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("domain_pack_version_id", UUID, nullable=False),
        sa.Column("dependency_pack_key", sa.String(63), nullable=False),
        sa.Column("requested_range", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "domain_pack_version_id"],
            ["domain_pack_versions.tenant_id", "domain_pack_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "domain_pack_version_id",
            "dependency_pack_key",
            name="uq_domain_pack_dependencies_key",
        ),
    )
    op.create_table(
        "domain_pack_revocations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("key_id", sa.String(128)),
        sa.Column("domain_pack_version_id", UUID),
        sa.Column("content_checksum", sa.String(71)),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("evidence_checksum", sa.String(71), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "domain_pack_version_id"],
            ["domain_pack_versions.tenant_id", "domain_pack_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "key_id IS NOT NULL OR domain_pack_version_id IS NOT NULL",
            name="ck_domain_pack_revocations_target",
        ),
        sa.CheckConstraint(
            f"content_checksum IS NULL OR content_checksum ~ '{CHECKSUM}'",
            name="ck_domain_pack_revocations_checksum",
        ),
        sa.CheckConstraint(
            f"evidence_checksum ~ '{CHECKSUM}'", name="ck_domain_pack_revocations_evidence"
        ),
    )
    op.create_table(
        "schema_version_pack_inputs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("domain_pack_version_id", UUID, nullable=False),
        sa.Column("input_order", sa.Integer(), nullable=False),
        sa.Column("content_checksum", sa.String(71), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "domain_pack_version_id"],
            ["domain_pack_versions.tenant_id", "domain_pack_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "schema_version_id",
            "domain_pack_version_id",
            name="uq_schema_version_pack_inputs_version",
        ),
        sa.UniqueConstraint(
            "schema_version_id", "input_order", name="uq_schema_version_pack_inputs_order"
        ),
        sa.CheckConstraint("input_order >= 0", name="ck_schema_version_pack_inputs_order"),
        sa.CheckConstraint(
            f"content_checksum ~ '{CHECKSUM}'", name="ck_schema_version_pack_inputs_checksum"
        ),
    )
    op.create_table(
        "domain_pack_installations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("domain_pack_version_id", UUID, nullable=False),
        sa.Column("schema_definition_id", UUID, nullable=False),
        sa.Column("requested_semantic_version", sa.String(64), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False, server_default="INSTALL"),
        sa.Column("previous_installation_id", UUID),
        sa.Column("workflow_task_id", UUID),
        sa.Column("workflow_id", sa.String(768), nullable=False),
        sa.Column("run_id", sa.String(255)),
        sa.Column("candidate_schema_version_id", UUID),
        sa.Column("composition_report_id", UUID),
        sa.Column("status", sa.String(32), nullable=False, server_default="PLANNED"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "domain_pack_version_id"],
            ["domain_pack_versions.tenant_id", "domain_pack_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_definition_id"],
            [
                "schema_definitions.tenant_id",
                "schema_definitions.space_id",
                "schema_definitions.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "previous_installation_id"],
            [
                "domain_pack_installations.tenant_id",
                "domain_pack_installations.space_id",
                "domain_pack_installations.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "workflow_task_id"],
            ["workflow_tasks.tenant_id", "workflow_tasks.space_id", "workflow_tasks.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "candidate_schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "tenant_id", "space_id", "id", name="uq_domain_pack_installations_scope_id"
        ),
        sa.CheckConstraint(
            "status IN ('PLANNED','INSTALLING','ACTIVE','FAILED','ROLLING_BACK','ROLLED_BACK','DISABLED')",
            name="ck_domain_pack_installations_status",
        ),
        sa.CheckConstraint(
            "operation IN ('INSTALL','UPGRADE','DISABLE','ROLLBACK')",
            name="ck_domain_pack_installations_operation",
        ),
        sa.CheckConstraint(
            "previous_installation_id IS NULL OR previous_installation_id <> id",
            name="ck_domain_pack_installations_previous",
        ),
    )
    op.create_table(
        "schema_composition_reports",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("schema_version_id", UUID, nullable=False),
        sa.Column("input_checksum", sa.String(71), nullable=False),
        sa.Column("result_checksum", sa.String(71), nullable=False),
        sa.Column("report", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        _scope_fk(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "schema_version_id"],
            ["schema_versions.tenant_id", "schema_versions.space_id", "schema_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "schema_version_id", "input_checksum", name="uq_schema_composition_reports_input"
        ),
        sa.UniqueConstraint(
            "tenant_id", "space_id", "id", name="uq_schema_composition_reports_scope_id"
        ),
        sa.CheckConstraint(
            f"input_checksum ~ '{CHECKSUM}' AND result_checksum ~ '{CHECKSUM}'",
            name="ck_schema_composition_reports_checksums",
        ),
    )
    op.create_foreign_key(
        "fk_domain_pack_installations_report",
        "domain_pack_installations",
        "schema_composition_reports",
        ["tenant_id", "space_id", "composition_report_id"],
        ["tenant_id", "space_id", "id"],
        ondelete="RESTRICT",
    )
    for table in (
        "entity_types",
        "relation_types",
        "property_definitions",
        "type_hierarchy_edges",
        "type_terms",
        "concept_mappings",
        "page_templates",
        "lint_rules",
        "evaluation_suites",
        "ui_declarations",
        "schema_migration_plans",
        "domain_pack_versions",
        "domain_pack_contents",
        "domain_pack_dependencies",
        "domain_pack_revocations",
        "schema_version_pack_inputs",
        "schema_composition_reports",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION prevent_nexweave_m3_fact_mutation()"
        )
    op.execute(
        """
        CREATE FUNCTION protect_nexweave_schema_version() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'SchemaVersion is not deletable';
          END IF;
          IF OLD.status IN ('PUBLISHED','DEPRECATED') AND (
             NEW.normalized_snapshot <> OLD.normalized_snapshot
             OR NEW.local_declarations <> OLD.local_declarations
             OR NEW.content_checksum <> OLD.content_checksum
             OR NEW.composition_checksum <> OLD.composition_checksum
             OR NEW.canonicalization_algorithm <> OLD.canonicalization_algorithm
             OR NEW.semantic_version <> OLD.semantic_version
             OR NEW.schema_definition_id <> OLD.schema_definition_id
          ) THEN
            RAISE EXCEPTION 'published SchemaVersion content is immutable';
          END IF;
          IF NOT (
            NEW.status = OLD.status
            OR (OLD.status = 'DRAFT' AND NEW.status = 'TESTING')
            OR (OLD.status IN ('DRAFT','TESTING') AND NEW.status = 'PUBLISHED')
            OR (OLD.status = 'PUBLISHED' AND NEW.status = 'DEPRECATED')
          ) THEN
            RAISE EXCEPTION 'SchemaVersion status transition is invalid';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER schema_versions_protect BEFORE UPDATE OR DELETE ON schema_versions "
        "FOR EACH ROW EXECUTE FUNCTION protect_nexweave_schema_version()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER schema_versions_protect ON schema_versions")
    op.execute("DROP FUNCTION protect_nexweave_schema_version")
    for table in (
        "schema_composition_reports",
        "schema_version_pack_inputs",
        "domain_pack_revocations",
        "domain_pack_dependencies",
        "domain_pack_contents",
        "domain_pack_versions",
        "schema_migration_plans",
        "evaluation_suites",
        "ui_declarations",
        "lint_rules",
        "page_templates",
        "concept_mappings",
        "type_terms",
        "type_hierarchy_edges",
        "property_definitions",
        "relation_types",
        "entity_types",
    ):
        op.execute(f"DROP TRIGGER {table}_append_only ON {table}")
    op.drop_constraint(
        "fk_domain_pack_installations_report",
        "domain_pack_installations",
        type_="foreignkey",
    )
    for table in (
        "domain_pack_installations",
        "schema_composition_reports",
        "schema_version_pack_inputs",
        "domain_pack_revocations",
        "domain_pack_dependencies",
        "domain_pack_contents",
        "domain_pack_versions",
        "domain_pack_trust_keys",
        "domain_packs",
        "schema_migration_plans",
        "evaluation_suites",
        "ui_declarations",
        "lint_rules",
        "page_templates",
        "concept_mappings",
        "type_terms",
        "type_hierarchy_edges",
        "property_definitions",
        "relation_types",
        "entity_types",
        "schema_versions",
        "schema_definitions",
    ):
        op.drop_table(table)
