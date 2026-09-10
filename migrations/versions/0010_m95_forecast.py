"""M9.5 scoped operational bindings and immutable numerical forecast artifacts."""

from collections.abc import Sequence

from alembic import op

revision: str = "0010_m95"
down_revision: str | None = "0009_m8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE signal_bindings (
          id uuid PRIMARY KEY, tenant_id uuid NOT NULL, space_id uuid NOT NULL,
          entity_id uuid NOT NULL, schema_version_id uuid NOT NULL, source_version_id uuid NOT NULL,
          classification varchar(32) NOT NULL, body jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(), created_by uuid NOT NULL,
          UNIQUE(tenant_id, space_id, id),
          FOREIGN KEY(tenant_id,space_id) REFERENCES knowledge_spaces(tenant_id,id),
          FOREIGN KEY(tenant_id,space_id,entity_id) REFERENCES knowledge_entities(tenant_id,space_id,id),
          FOREIGN KEY(tenant_id,space_id,schema_version_id) REFERENCES schema_versions(tenant_id,space_id,id),
          FOREIGN KEY(tenant_id,space_id,source_version_id) REFERENCES source_versions(tenant_id,space_id,id),
          CHECK(classification IN ('PUBLIC','INTERNAL','CONFIDENTIAL','HIGHLY_RESTRICTED'))
        )
    """)
    op.execute("""
        CREATE TABLE forecast_runs (
          id uuid PRIMARY KEY, tenant_id uuid NOT NULL, space_id uuid NOT NULL,
          binding_id uuid NOT NULL, classification varchar(32) NOT NULL,
          request jsonb NOT NULL, principal_snapshot jsonb NOT NULL, model_revision varchar(128) NOT NULL,
          status varchar(16) NOT NULL DEFAULT 'QUEUED', workflow_id varchar(255) NOT NULL UNIQUE,
          artifact_id uuid, error_code varchar(128), context jsonb,
          created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
          created_by uuid NOT NULL,
          UNIQUE(tenant_id,space_id,id),
          FOREIGN KEY(tenant_id,space_id,binding_id) REFERENCES signal_bindings(tenant_id,space_id,id),
          CHECK(status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED'))
        )
    """)
    op.execute("""
        CREATE TABLE forecast_artifacts (
          id uuid PRIMARY KEY, tenant_id uuid NOT NULL, space_id uuid NOT NULL,
          run_id uuid NOT NULL UNIQUE, classification varchar(32) NOT NULL,
          data_kind varchar(32) NOT NULL, content_checksum varchar(71) NOT NULL,
          object_key varchar(512) NOT NULL, content jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE(tenant_id,space_id,id),
          FOREIGN KEY(tenant_id,space_id,run_id) REFERENCES forecast_runs(tenant_id,space_id,id),
          CHECK(data_kind IN ('SYNTHETIC','IMPORTED_UNVERIFIED')),
          CHECK(content_checksum ~ '^sha256:[0-9a-f]{64}$')
        )
    """)
    op.execute("""ALTER TABLE forecast_runs ADD CONSTRAINT fk_forecast_run_artifact
        FOREIGN KEY(tenant_id,space_id,artifact_id)
        REFERENCES forecast_artifacts(tenant_id,space_id,id)""")
    for table in ("signal_bindings", "forecast_artifacts"):
        op.execute(f"""CREATE TRIGGER {table}_m95_immutable BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION nexweave_m5_immutable_guard()""")
    op.execute("""
        CREATE FUNCTION nexweave_m95_run_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP='DELETE' THEN RAISE EXCEPTION 'forecast run is retained'; END IF;
          IF OLD.status IN ('SUCCEEDED','FAILED','CANCELLED') OR
             (to_jsonb(NEW) - ARRAY['status','artifact_id','error_code','context','updated_at'])
             IS DISTINCT FROM
             (to_jsonb(OLD) - ARRAY['status','artifact_id','error_code','context','updated_at']) OR
             (OLD.context IS NOT NULL AND OLD.context IS DISTINCT FROM NEW.context)
          THEN RAISE EXCEPTION 'forecast locked input or terminal result is immutable'; END IF;
          RETURN NEW;
        END $$
    """)
    op.execute("""CREATE TRIGGER forecast_runs_guard BEFORE UPDATE OR DELETE ON forecast_runs
        FOR EACH ROW EXECUTE FUNCTION nexweave_m95_run_guard()
    """)

    op.create_index(
        "ix_signal_bindings_space", "signal_bindings", ["tenant_id", "space_id", "created_at"]
    )
    op.create_index(
        "ix_forecast_runs_space", "forecast_runs", ["tenant_id", "space_id", "created_at"]
    )


def downgrade() -> None:
    op.execute("ALTER TABLE forecast_runs DROP CONSTRAINT fk_forecast_run_artifact")
    op.drop_table("forecast_artifacts")
    op.drop_table("forecast_runs")
    op.drop_table("signal_bindings")
    op.execute("DROP FUNCTION nexweave_m95_run_guard()")
