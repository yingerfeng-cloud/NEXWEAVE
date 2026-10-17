"""Schedule independent retries without a poisoned review blocking other cases."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_r1_delivery"
down_revision: str | None = "0014_r1_semantic"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "review_deliveries",
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_review_deliveries_due",
        "review_deliveries",
        ["next_attempt_at", "created_at"],
        postgresql_where=sa.text("delivered_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_review_deliveries_due", table_name="review_deliveries")
    op.drop_column("review_deliveries", "next_attempt_at")
