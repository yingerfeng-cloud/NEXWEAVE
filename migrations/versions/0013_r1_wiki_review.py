"""Allow authoritative review of immutable Wiki versions.

Revision ID: 0013_r1_wiki
Revises: 0012_r1_review
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013_r1_wiki"
down_revision: str | None = "0012_r1_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_review_cases_target", "review_cases", type_="check")
    op.create_check_constraint(
        "ck_review_cases_target",
        "review_cases",
        "target_type IN ('CLAIM_CANDIDATE','RELATION_CANDIDATE','SEMANTIC_PROPOSAL','WIKI_PAGE_VERSION')",
    )


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM review_cases WHERE target_type='WIKI_PAGE_VERSION') THEN
            RAISE EXCEPTION 'Wiki review history exists: preserve it and roll forward; restore a pre-upgrade backup for a full rollback';
          END IF;
        END $$
    """)
    op.drop_constraint("ck_review_cases_target", "review_cases", type_="check")
    op.create_check_constraint(
        "ck_review_cases_target",
        "review_cases",
        "target_type IN ('CLAIM_CANDIDATE','RELATION_CANDIDATE','SEMANTIC_PROPOSAL')",
    )
