"""add_activity_product_co_view_scores

Revision ID: c9f1d2a3b7e4
Revises: 7b21e0a9c401
Create Date: 2026-04-22 06:00:00.000000

Phase B2 of the recommendation roadmap.  Stores pairwise product co-view
scores derived from ``user_activity_events``.  Refreshed hourly by
``refresh_co_view_scores_task``.

The table is intentionally denormalised and stores both directions
(``product_id -> co_product_id`` and vice versa) so "also viewed" queries
hit a single (product_id, score DESC) index without a UNION.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9f1d2a3b7e4"
down_revision: str | Sequence[str] | None = "7b21e0a9c401"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE product_co_view_scores (
            product_id UUID NOT NULL,
            co_product_id UUID NOT NULL,
            score INTEGER NOT NULL,
            computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_product_co_view_scores
                PRIMARY KEY (product_id, co_product_id),
            CONSTRAINT ck_product_co_view_scores_distinct
                CHECK (product_id <> co_product_id),
            CONSTRAINT ck_product_co_view_scores_positive
                CHECK (score > 0)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_product_co_view_scores_top "
        "ON product_co_view_scores (product_id, score DESC)"
    )
    op.execute(
        "CREATE INDEX ix_product_co_view_scores_computed_at "
        "ON product_co_view_scores (computed_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS product_co_view_scores")
