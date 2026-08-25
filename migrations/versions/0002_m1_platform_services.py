"""Add M1 identity, workspace, governance and managed-object services.

Revision ID: 0002_m1
Revises: 0001_m0
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_m1"
down_revision: str | None = "0001_m0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
UTC_NOW = sa.text("CURRENT_TIMESTAMP")
CLASSIFICATION = "('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'HIGHLY_RESTRICTED')"
BASE_ROLES = (
    "('platform_admin', 'tenant_admin', 'space_admin', 'knowledge_engineer', "
    "'reviewer', 'publisher', 'consumer', 'auditor', 'service')"
)


def _audit_columns(*, mutable: bool = True) -> list[sa.Column[object]]:
    columns: list[sa.Column[object]] = [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column("created_by", UUID, nullable=False),
    ]
    if mutable:
        columns.extend(
            [
                sa.Column(
                    "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW
                ),
                sa.Column("updated_by", UUID, nullable=False),
            ]
        )
    return columns


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
    )
    op.add_column("organizations", sa.Column("archived_at", sa.DateTime(timezone=True)))
    op.create_check_constraint(
        "ck_organizations_status", "organizations", "status IN ('ACTIVE', 'ARCHIVED')"
    )

    op.add_column(
        "user_identities",
        sa.Column("clearance", sa.String(32), nullable=False, server_default="INTERNAL"),
    )
    op.add_column("user_identities", sa.Column("archived_at", sa.DateTime(timezone=True)))
    op.create_check_constraint(
        "ck_user_identities_clearance", "user_identities", f"clearance IN {CLASSIFICATION}"
    )

    op.add_column(
        "service_identities",
        sa.Column("clearance", sa.String(32), nullable=False, server_default="INTERNAL"),
    )
    op.add_column("service_identities", sa.Column("credential_ref", sa.String(512)))
    op.add_column("service_identities", sa.Column("archived_at", sa.DateTime(timezone=True)))
    op.create_check_constraint(
        "ck_service_identities_clearance",
        "service_identities",
        f"clearance IN {CLASSIFICATION}",
    )
    op.create_check_constraint(
        "ck_service_identities_credential_ref",
        "service_identities",
        "credential_ref IS NULL OR credential_ref ~ '^(env|vault|secret|kms)://[A-Za-z0-9._/-]+$'",
    )

    op.add_column(
        "knowledge_spaces",
        sa.Column("description", sa.String(2000), nullable=False, server_default=""),
    )
    op.add_column("knowledge_spaces", sa.Column("archived_at", sa.DateTime(timezone=True)))

    op.create_table(
        "service_identity_audiences",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("service_identity_id", UUID, nullable=False),
        sa.Column("audience", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "service_identity_id"],
            ["service_identities.tenant_id", "service_identities.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("tenant_id", "service_identity_id", "audience"),
    )

    op.create_table(
        "tenant_role_assignments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("user_identity_id", UUID),
        sa.Column("service_identity_id", UUID),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_identity_id"],
            ["user_identities.tenant_id", "user_identities.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "service_identity_id"],
            ["service_identities.tenant_id", "service_identities.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(subject_type = 'USER' AND user_identity_id IS NOT NULL AND service_identity_id IS NULL) "
            "OR (subject_type = 'SERVICE' AND user_identity_id IS NULL AND service_identity_id IS NOT NULL)",
            name="ck_tenant_roles_subject",
        ),
        sa.CheckConstraint(f"role IN {BASE_ROLES}", name="ck_tenant_roles_role"),
        sa.CheckConstraint("status IN ('ACTIVE', 'REVOKED')", name="ck_tenant_roles_status"),
        sa.CheckConstraint("version >= 1", name="ck_tenant_roles_version"),
    )
    op.create_index(
        "uq_tenant_roles_user_active",
        "tenant_role_assignments",
        ["tenant_id", "user_identity_id", "role"],
        unique=True,
        postgresql_where=sa.text("subject_type = 'USER' AND status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_tenant_roles_service_active",
        "tenant_role_assignments",
        ["tenant_id", "service_identity_id", "role"],
        unique=True,
        postgresql_where=sa.text("subject_type = 'SERVICE' AND status = 'ACTIVE'"),
    )

    op.create_table(
        "space_members",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("user_identity_id", UUID),
        sa.Column("service_identity_id", UUID),
        sa.Column("clearance", sa.String(32), nullable=False, server_default="INTERNAL"),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id"],
            ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_identity_id"],
            ["user_identities.tenant_id", "user_identities.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "service_identity_id"],
            ["service_identities.tenant_id", "service_identities.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_space_members_scope_id"),
        sa.CheckConstraint(
            "(subject_type = 'USER' AND user_identity_id IS NOT NULL AND service_identity_id IS NULL) "
            "OR (subject_type = 'SERVICE' AND user_identity_id IS NULL AND service_identity_id IS NOT NULL)",
            name="ck_space_members_subject",
        ),
        sa.CheckConstraint(f"clearance IN {CLASSIFICATION}", name="ck_space_members_clearance"),
        sa.CheckConstraint("status IN ('ACTIVE', 'REVOKED')", name="ck_space_members_status"),
        sa.CheckConstraint("version >= 1", name="ck_space_members_version"),
    )
    op.create_index(
        "uq_space_members_user_active",
        "space_members",
        ["tenant_id", "space_id", "user_identity_id"],
        unique=True,
        postgresql_where=sa.text("subject_type = 'USER' AND status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_space_members_service_active",
        "space_members",
        ["tenant_id", "space_id", "service_identity_id"],
        unique=True,
        postgresql_where=sa.text("subject_type = 'SERVICE' AND status = 'ACTIVE'"),
    )

    op.create_table(
        "space_member_roles",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("space_member_id", UUID, nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "space_member_id"],
            ["space_members.tenant_id", "space_members.space_id", "space_members.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tenant_id", "space_id", "space_member_id", "role"),
        sa.CheckConstraint(f"role IN {BASE_ROLES}", name="ck_space_member_roles_role"),
    )

    op.create_table(
        "idempotency_records",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("actor_id", UUID, nullable=False),
        sa.Column("operation", sa.String(255), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(71), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", JSONB, nullable=False),
        sa.Column("resource_id", UUID),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(mutable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "tenant_id", "actor_id", "operation", "idempotency_key", name="uq_idempotency_scope"
        ),
        sa.CheckConstraint(
            "request_hash ~ '^sha256:[0-9a-f]{64}$'", name="ck_idempotency_request_hash"
        ),
    )

    op.create_table(
        "model_profiles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(128), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("credential_ref", sa.String(512)),
        sa.Column("externally_hosted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "maximum_classification", sa.String(32), nullable=False, server_default="INTERNAL"
        ),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id"],
            ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_model_profiles_scope_id"),
        sa.CheckConstraint(
            f"maximum_classification IN {CLASSIFICATION}", name="ck_model_profiles_classification"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'DISABLED', 'DEPRECATED')",
            name="ck_model_profiles_status",
        ),
        sa.CheckConstraint(
            "credential_ref IS NULL OR credential_ref ~ '^(env|vault|secret|kms)://[A-Za-z0-9._/-]+$'",
            name="ck_model_profiles_credential_ref",
        ),
        sa.CheckConstraint(
            "NOT (externally_hosted AND maximum_classification = 'HIGHLY_RESTRICTED')",
            name="ck_model_profiles_external_restricted",
        ),
        sa.CheckConstraint("version >= 1", name="ck_model_profiles_version"),
    )
    op.create_index("ix_model_profiles_tenant_space", "model_profiles", ["tenant_id", "space_id"])

    op.create_table(
        "prompt_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID),
        sa.Column("prompt_key", sa.String(255), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("output_contract", JSONB, nullable=False, server_default="{}"),
        sa.Column("checksum", sa.String(71), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        *_audit_columns(mutable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id"],
            ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_prompt_versions_scope_id"),
        sa.CheckConstraint("revision >= 1", name="ck_prompt_versions_revision"),
        sa.CheckConstraint(
            "checksum ~ '^sha256:[0-9a-f]{64}$'", name="ck_prompt_versions_checksum"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'DEPRECATED')", name="ck_prompt_versions_status"
        ),
    )
    op.create_index(
        "uq_prompt_versions_tenant_key_revision",
        "prompt_versions",
        ["tenant_id", "prompt_key", "revision"],
        unique=True,
        postgresql_where=sa.text("space_id IS NULL"),
    )
    op.create_index(
        "uq_prompt_versions_space_key_revision",
        "prompt_versions",
        ["tenant_id", "space_id", "prompt_key", "revision"],
        unique=True,
        postgresql_where=sa.text("space_id IS NOT NULL"),
    )

    op.create_table(
        "connector_definitions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("connector_type", sa.String(128), nullable=False),
        sa.Column("config_schema", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id"],
            ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_connector_definitions_scope_id"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'DISABLED')",
            name="ck_connector_definitions_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_connector_definitions_version"),
    )
    op.create_index(
        "uq_connector_definitions_tenant_type",
        "connector_definitions",
        ["tenant_id", "connector_type"],
        unique=True,
        postgresql_where=sa.text("space_id IS NULL"),
    )
    op.create_index(
        "uq_connector_definitions_space_type",
        "connector_definitions",
        ["tenant_id", "space_id", "connector_type"],
        unique=True,
        postgresql_where=sa.text("space_id IS NOT NULL"),
    )

    op.create_table(
        "object_upload_sessions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("expected_size", sa.BigInteger(), nullable=False),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="INITIATED"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_object_id", UUID),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id"],
            ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "tenant_id", "space_id", "id", name="uq_object_upload_sessions_scope_id"
        ),
        sa.CheckConstraint("expected_size > 0", name="ck_object_upload_sessions_size"),
        sa.CheckConstraint(
            f"classification IN {CLASSIFICATION}", name="ck_object_upload_sessions_classification"
        ),
        sa.CheckConstraint(
            "status IN ('INITIATED', 'UPLOADING', 'COMPLETED', 'ABORTED', 'EXPIRED')",
            name="ck_object_upload_sessions_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_object_upload_sessions_version"),
    )

    op.create_table(
        "managed_objects",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("space_id", UUID, nullable=False),
        sa.Column("upload_session_id", UUID, nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("object_key", sa.String(1024), nullable=False),
        sa.Column("object_version_id", sa.String(255)),
        sa.Column("checksum", sa.String(71), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("scan_status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id"],
            ["knowledge_spaces.tenant_id", "knowledge_spaces.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id", "upload_session_id"],
            [
                "object_upload_sessions.tenant_id",
                "object_upload_sessions.space_id",
                "object_upload_sessions.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "space_id", "id", name="uq_managed_objects_scope_id"),
        sa.UniqueConstraint("object_key", name="uq_managed_objects_key"),
        sa.CheckConstraint(
            "checksum ~ '^sha256:[0-9a-f]{64}$'", name="ck_managed_objects_checksum"
        ),
        sa.CheckConstraint("size > 0", name="ck_managed_objects_size"),
        sa.CheckConstraint(
            f"classification IN {CLASSIFICATION}", name="ck_managed_objects_classification"
        ),
        sa.CheckConstraint(
            "scan_status IN ('PENDING', 'CLEAN', 'INFECTED', 'FAILED')",
            name="ck_managed_objects_scan_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_managed_objects_version"),
    )
    op.create_index("ix_managed_objects_tenant_space", "managed_objects", ["tenant_id", "space_id"])

    op.create_foreign_key(
        "fk_object_upload_sessions_completed_object",
        "object_upload_sessions",
        "managed_objects",
        ["tenant_id", "space_id", "completed_object_id"],
        ["tenant_id", "space_id", "id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_object_upload_sessions_completed_object", "object_upload_sessions", type_="foreignkey"
    )
    op.drop_index("ix_managed_objects_tenant_space", table_name="managed_objects")
    op.drop_table("managed_objects")
    op.drop_table("object_upload_sessions")
    # M1 was still unaccepted while these indexes were introduced. IF EXISTS keeps local
    # development databases created by the earlier M1 draft safely downgradeable.
    op.execute("DROP INDEX IF EXISTS uq_connector_definitions_space_type")
    op.execute("DROP INDEX IF EXISTS uq_connector_definitions_tenant_type")
    op.drop_table("connector_definitions")
    op.drop_index("uq_prompt_versions_space_key_revision", table_name="prompt_versions")
    op.drop_index("uq_prompt_versions_tenant_key_revision", table_name="prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_index("ix_model_profiles_tenant_space", table_name="model_profiles")
    op.drop_table("model_profiles")
    op.drop_table("idempotency_records")
    op.drop_table("space_member_roles")
    op.drop_index("uq_space_members_service_active", table_name="space_members")
    op.drop_index("uq_space_members_user_active", table_name="space_members")
    op.drop_table("space_members")
    op.drop_index("uq_tenant_roles_service_active", table_name="tenant_role_assignments")
    op.drop_index("uq_tenant_roles_user_active", table_name="tenant_role_assignments")
    op.drop_table("tenant_role_assignments")
    op.drop_table("service_identity_audiences")

    op.drop_column("knowledge_spaces", "archived_at")
    op.drop_column("knowledge_spaces", "description")

    op.drop_constraint("ck_service_identities_credential_ref", "service_identities", type_="check")
    op.drop_constraint("ck_service_identities_clearance", "service_identities", type_="check")
    op.drop_column("service_identities", "archived_at")
    op.drop_column("service_identities", "credential_ref")
    op.drop_column("service_identities", "clearance")

    op.drop_constraint("ck_user_identities_clearance", "user_identities", type_="check")
    op.drop_column("user_identities", "archived_at")
    op.drop_column("user_identities", "clearance")

    op.drop_constraint("ck_organizations_status", "organizations", type_="check")
    op.drop_column("organizations", "archived_at")
    op.drop_column("organizations", "status")
