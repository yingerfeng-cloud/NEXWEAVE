"""Create the M0 platform foundation without knowledge business tables.

Revision ID: 0001_m0
Revises: None
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_m0"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UUID = postgresql.UUID(as_uuid=True)
UTC_NOW = sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("slug", sa.String(63), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'SUSPENDED', 'CLOSED')", name="ck_tenants_status"),
        sa.CheckConstraint("version >= 1", name="ck_tenants_version"),
        sa.UniqueConstraint("id", "slug", name="uq_tenants_id_slug"),
    )

    op.create_table(
        "organizations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("slug", sa.String(63), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_organizations_tenant_id_id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_organizations_tenant_slug"),
        sa.CheckConstraint("version >= 1", name="ck_organizations_version"),
    )

    op.create_table(
        "user_identities",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("issuer", sa.String(512), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_user_identities_tenant_id_id"),
        sa.UniqueConstraint("tenant_id", "issuer", "subject", name="uq_user_identities_oidc"),
        sa.CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="ck_user_identities_status"),
        sa.CheckConstraint("version >= 1", name="ck_user_identities_version"),
    )

    op.create_table(
        "service_identities",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_service_identities_tenant_id_id"),
        sa.UniqueConstraint("tenant_id", "client_id", name="uq_service_identities_client_id"),
        sa.CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="ck_service_identities_status"),
        sa.CheckConstraint("version >= 1", name="ck_service_identities_version"),
    )

    op.create_table(
        "knowledge_spaces",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("slug", sa.String(63), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column(
            "default_classification", sa.String(32), nullable=False, server_default="INTERNAL"
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("updated_by", UUID, nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_knowledge_spaces_tenant_id_id"),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "slug", name="uq_knowledge_spaces_slug"
        ),
        sa.CheckConstraint(
            "default_classification IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'HIGHLY_RESTRICTED')",
            name="ck_knowledge_spaces_classification",
        ),
        sa.CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name="ck_knowledge_spaces_status"),
        sa.CheckConstraint("version >= 1", name="ck_knowledge_spaces_version"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW
        ),
        sa.Column("actor_type", sa.String(32), nullable=False),
        sa.Column("actor_id", UUID, nullable=False),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(128), nullable=False),
        sa.Column("resource_id", UUID, nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("correlation_id", UUID, nullable=True),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id"],
            ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "actor_type IN ('USER', 'SERVICE', 'SYSTEM')", name="ck_audit_logs_actor_type"
        ),
        sa.CheckConstraint(
            "outcome IN ('SUCCEEDED', 'DENIED', 'FAILED')", name="ck_audit_logs_outcome"
        ),
    )
    op.create_index("ix_audit_logs_tenant_occurred", "audit_logs", ["tenant_id", "occurred_at"])
    op.execute(
        """
        CREATE FUNCTION prevent_nexweave_audit_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_append_only
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_nexweave_audit_mutation()
        """
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=True),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("aggregate_type", sa.String(128), nullable=False),
        sa.Column("aggregate_id", UUID, nullable=False),
        sa.Column("aggregate_version", sa.BigInteger(), nullable=False),
        sa.Column("correlation_id", UUID, nullable=False),
        sa.Column("causation_id", UUID, nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publish_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(128), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id"],
            ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("aggregate_version >= 1", name="ck_outbox_events_aggregate_version"),
        sa.CheckConstraint("publish_attempts >= 0", name="ck_outbox_events_publish_attempts"),
    )
    op.create_index(
        "ix_outbox_events_unpublished",
        "outbox_events",
        ["occurred_at"],
        postgresql_where=sa.text("published_at IS NULL"),
    )

    op.create_table(
        "system_configurations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("tenant_id", UUID, nullable=True),
        sa.Column("space_id", UUID, nullable=True),
        sa.Column("config_key", sa.String(255), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("contains_secret", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
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
        sa.CheckConstraint(
            "scope IN ('PLATFORM', 'TENANT', 'SPACE')", name="ck_system_config_scope"
        ),
        sa.CheckConstraint(
            "(scope = 'PLATFORM' AND tenant_id IS NULL AND space_id IS NULL) OR "
            "(scope = 'TENANT' AND tenant_id IS NOT NULL AND space_id IS NULL) OR "
            "(scope = 'SPACE' AND tenant_id IS NOT NULL AND space_id IS NOT NULL)",
            name="ck_system_config_scope_keys",
        ),
        sa.CheckConstraint("contains_secret = false", name="ck_system_config_no_inline_secrets"),
        sa.CheckConstraint("version >= 1", name="ck_system_config_version"),
    )
    op.create_index(
        "uq_system_config_platform_key",
        "system_configurations",
        ["config_key"],
        unique=True,
        postgresql_where=sa.text("scope = 'PLATFORM'"),
    )
    op.create_index(
        "uq_system_config_tenant_key",
        "system_configurations",
        ["tenant_id", "config_key"],
        unique=True,
        postgresql_where=sa.text("scope = 'TENANT'"),
    )
    op.create_index(
        "uq_system_config_space_key",
        "system_configurations",
        ["tenant_id", "space_id", "config_key"],
        unique=True,
        postgresql_where=sa.text("scope = 'SPACE'"),
    )

    op.create_table(
        "platform_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("release_name", sa.String(32), nullable=False),
        sa.Column("milestone", sa.String(32), nullable=False),
        sa.Column("build_version", sa.String(128), nullable=False, unique=True),
        sa.Column("migration_revision", sa.String(128), nullable=False),
        sa.Column(
            "installed_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW
        ),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"
        ),
    )


def downgrade() -> None:
    op.drop_table("platform_versions")
    op.drop_table("system_configurations")
    op.drop_index("ix_outbox_events_unpublished", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_audit_logs_tenant_occurred", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.execute("DROP FUNCTION prevent_nexweave_audit_mutation()")
    op.drop_table("knowledge_spaces")
    op.drop_table("service_identities")
    op.drop_table("user_identities")
    op.drop_table("organizations")
    op.drop_table("tenants")
