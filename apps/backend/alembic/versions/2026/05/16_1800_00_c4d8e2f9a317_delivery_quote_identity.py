"""add delivery_quotes.identity_id for quote ownership (CR-2)

The customer checkout endpoint /storefront/logistics/rates/quote now
stamps the requesting Identity onto each persisted quote so the
follow-up order creation can refuse a quote that belongs to a
different customer (CR-2 from the post-merge review). Nullable so
admin-side quoting (where the operator quotes on behalf of an
not-yet-known buyer) and the pre-existing legacy rows keep working
without backfill.

Revision ID: c4d8e2f9a317
Revises: d2e8a4f1c537
Create Date: 2026-05-16 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c4d8e2f9a317"
down_revision: str | Sequence[str] | None = "d2e8a4f1c537"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "delivery_quotes",
        sa.Column(
            "identity_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_delivery_quotes_identity",
        "delivery_quotes",
        ["identity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_delivery_quotes_identity", table_name="delivery_quotes")
    op.drop_column("delivery_quotes", "identity_id")
