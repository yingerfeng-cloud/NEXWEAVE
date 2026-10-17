"""Bind R1 reviews to immutable server-side content revisions.

Revision ID: 0012_r1_review
Revises: 0011_m95a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_r1_review"
down_revision: str | None = "0011_m95a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_target_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("content_checksum", sa.String(71), nullable=False),
        sa.Column("original_author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edited_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["review_case_id"], ["review_cases.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("review_case_id", "revision", name="uq_review_target_revision"),
    )
    # Existing open cases have no proven reviewed version. Do not invent a past
    # snapshot: they fail closed until explicitly superseded with a fresh case.
    op.execute("""
        CREATE TRIGGER review_target_revisions_immutable BEFORE UPDATE OR DELETE
        ON review_target_revisions FOR EACH ROW
        EXECUTE FUNCTION nexweave_m5_immutable_guard()
    """)
    op.create_table(
        "review_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(64)),
        sa.ForeignKeyConstraint(["review_case_id"], ["review_cases.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("review_case_id", "kind", name="uq_review_delivery"),
        sa.CheckConstraint("kind IN ('START','DECISION')", name="ck_review_delivery_kind"),
    )


def downgrade() -> None:
    op.drop_table("review_deliveries")
    op.execute("DROP TRIGGER review_target_revisions_immutable ON review_target_revisions")
    op.drop_table("review_target_revisions")
