"""add_sku_pricing_history

Revision ID: f2c93a8e54b1
Revises: e8b3c721d49a
Create Date: 2026-04-25 18:00:00.000000

ADR-005 — append-only audit trail of every SKU pricing recompute
outcome. One row per state change (no rows for hash-match no-ops);
together with the SKU row itself it forms a fully reconstructable
history of how a selling price arrived at its current value.

Retention: 365 days, pruned by a separate cron task (Pass 4). Until
the cron lands the table just grows; on a 100k-SKU catalog with one
recompute/day per SKU that's ~36M rows/year, comfortably handled by
the ``(sku_id, recorded_at DESC)`` index.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f2c93a8e54b1"
down_revision: str | Sequence[str] | None = "e8b3c721d49a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sku_pricing_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "sku_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skus.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recorded_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("selling_price", sa.Integer(), nullable=True),
        sa.Column("selling_currency", sa.String(length=3), nullable=True),
        sa.Column(
            "formula_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("inputs_hash", sa.String(length=64), nullable=True),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "new_status IN ('legacy', 'pending', 'priced', 'stale_fx', "
            "'missing_purchase_price', 'formula_error')",
            name="ck_sku_pricing_history_status_enum",
        ),
        comment="Append-only audit trail of SKU pricing recompute outcomes (ADR-005)",
    )
    op.create_index(
        "ix_sku_pricing_history_sku_recorded",
        "sku_pricing_history",
        ["sku_id", sa.text("recorded_at DESC")],
    )
    op.create_index(
        "ix_sku_pricing_history_recorded_at",
        "sku_pricing_history",
        ["recorded_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sku_pricing_history_recorded_at",
        table_name="sku_pricing_history",
    )
    op.drop_index(
        "ix_sku_pricing_history_sku_recorded",
        table_name="sku_pricing_history",
    )
    op.drop_table("sku_pricing_history")
