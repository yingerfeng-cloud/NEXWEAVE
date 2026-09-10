"""Durable forecast delivery and ephemeral worker health for Stage A."""

from collections.abc import Sequence

from alembic import op

revision: str = "0011_m95a"
down_revision: str | None = "0010_m95"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""CREATE TABLE forecast_delivery (
        run_id uuid PRIMARY KEY REFERENCES forecast_runs(id),
        workflow_name varchar(128) NOT NULL,
        trace_id varchar(32) NOT NULL CHECK(trace_id ~ '^[0-9a-f]{32}$'),
        status varchar(16) NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','ACCEPTED','RETRYING','TERMINAL')),
        attempts integer NOT NULL DEFAULT 0 CHECK(attempts>=0),
        error_code varchar(128), cancel_pending boolean NOT NULL DEFAULT false,
        retry_of uuid REFERENCES forecast_runs(id),
        next_attempt_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""")
    op.execute("""INSERT INTO forecast_delivery(run_id,workflow_name,trace_id,status)
        SELECT id,'nexweave.forecast.v1',replace(id::text,'-',''),
            CASE WHEN status IN ('SUCCEEDED','FAILED','CANCELLED') THEN 'TERMINAL' ELSE 'PENDING' END
        FROM forecast_runs""")
    op.create_index("ix_forecast_delivery_due", "forecast_delivery", ["next_attempt_at"])
    op.execute("""CREATE TABLE forecast_worker_leases (
        id uuid PRIMARY KEY, queue varchar(128) NOT NULL, implementation_version varchar(64) NOT NULL,
        model_revision varchar(128) NOT NULL, ready boolean NOT NULL,
        seen_at timestamptz NOT NULL DEFAULT now()
    )""")


def downgrade() -> None:
    op.drop_table("forecast_worker_leases")
    op.drop_table("forecast_delivery")
