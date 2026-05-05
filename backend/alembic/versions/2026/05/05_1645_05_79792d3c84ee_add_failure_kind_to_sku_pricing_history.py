"""add_failure_kind_to_sku_pricing_history

Revision ID: 79792d3c84ee
Revises: b1c4d7e2a830
Create Date: 2026-05-05 16:45:05.316539

Per ADR-005a Open Issue #3 — adds a failure_kind discriminator to
the sku_pricing_history audit table so analytics can separate
optimistic-lock retry exhaustion (``"retry_exhausted"``) from
ordinary formula-error transitions. Nullable, no backfill needed
(existing rows keep failure_kind = NULL, semantically equivalent
to "ordinary failure").

The corresponding ORM column was added to SkuPricingHistoryModel
in PR-S6 commit 4/8; this migration brings the SQL schema in line
so integration tests landing in commit 7/8 can persist the field.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "79792d3c84ee"
down_revision: str | Sequence[str] | None = "b1c4d7e2a830"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "sku_pricing_history",
        sa.Column("failure_kind", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sku_pricing_history", "failure_kind")
