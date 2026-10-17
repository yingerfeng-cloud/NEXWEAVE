"""Real model projection provenance; preserve legacy hash vectors unused.

Revision ID: 0014_r1_semantic
Revises: 0013_r1_wiki
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_r1_semantic"
down_revision: str | None = "0013_r1_wiki"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE release_search_documents ALTER COLUMN embedding DROP NOT NULL")
    op.add_column("release_search_documents", sa.Column("semantic_embedding", postgresql.JSONB()))
    op.add_column("release_search_documents", sa.Column("embedding_fingerprint", sa.String(71)))
    op.create_table(
        "model_gateway_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("profile_fingerprint", sa.String(71), nullable=False),
        sa.Column("declared_revision", sa.String(255), nullable=False),
        sa.Column("response_model", sa.String(255), nullable=False),
        sa.Column("provider_request_id", sa.String(255), nullable=False),
        sa.Column("input_checksum", sa.String(71), nullable=False),
        sa.Column("output_checksum", sa.String(71), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["model_profile_id"], ["model_profiles.id"], ondelete="RESTRICT"),
    )
    op.execute(
        "CREATE TRIGGER model_gateway_calls_immutable BEFORE UPDATE OR DELETE ON model_gateway_calls FOR EACH ROW EXECUTE FUNCTION nexweave_m5_immutable_guard()"
    )


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM model_gateway_calls) OR EXISTS
        (SELECT 1 FROM release_search_documents WHERE embedding IS NULL) THEN
        RAISE EXCEPTION 'New model audit/projection data exists: preserve history and roll forward or restore pre-upgrade backup';
      END IF;
    END $$""")
    op.drop_table("model_gateway_calls")
    op.drop_column("release_search_documents", "embedding_fingerprint")
    op.drop_column("release_search_documents", "semantic_embedding")
    op.execute("ALTER TABLE release_search_documents ALTER COLUMN embedding SET NOT NULL")
