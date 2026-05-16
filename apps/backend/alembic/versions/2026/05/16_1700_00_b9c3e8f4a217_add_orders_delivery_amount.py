"""add orders.delivery_quote_id and orders.delivery_amount

Two columns persist the checkout shipping breakdown so the customer's
final invoice survives the logistics module pruning the delivery_quotes
row on TTL. ``delivery_amount`` is included in ``total_amount`` (the
payment authorization holds funds for goods + shipping in a single
operation); ``delivery_quote_id`` is a soft reference (no FK constraint)
because quotes are short-lived while orders are retained for years.

``server_default="0"`` lets the migration backfill the historic rows
without a table scan; new rows always set the value explicitly so the
default is only ever exercised in the rare case of a direct INSERT.

Revision ID: b9c3e8f4a217
Revises: f1a2b3c4d504
Create Date: 2026-05-16 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b9c3e8f4a217"
down_revision: str | Sequence[str] | None = "f1a2b3c4d504"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "delivery_quote_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "delivery_amount",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_orders_delivery_amount_nonnegative",
        "orders",
        "delivery_amount >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_orders_delivery_amount_nonnegative",
        "orders",
        type_="check",
    )
    op.drop_column("orders", "delivery_amount")
    op.drop_column("orders", "delivery_quote_id")
