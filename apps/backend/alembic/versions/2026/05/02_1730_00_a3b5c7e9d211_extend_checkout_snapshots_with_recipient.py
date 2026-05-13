"""extend cart.checkout_snapshots with pickup_carrier + recipient_id

Revision ID: a3b5c7e9d211
Revises: e8d2a4f1c937
Create Date: 2026-05-02 17:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a3b5c7e9d211"
down_revision: str | Sequence[str] | None = "e8d2a4f1c937"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "checkout_snapshots",
        sa.Column(
            "pickup_carrier",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'cdek'"),
        ),
    )
    op.add_column(
        "checkout_snapshots",
        sa.Column(
            "recipient_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_checkout_snapshots_recipient_id",
        "checkout_snapshots",
        ["recipient_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_checkout_snapshots_recipient_id", table_name="checkout_snapshots")
    op.drop_column("checkout_snapshots", "recipient_id")
    op.drop_column("checkout_snapshots", "pickup_carrier")
