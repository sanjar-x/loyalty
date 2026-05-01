"""add shipment cross_border_arrived_at + dobropost provider

Adds the ``shipments.cross_border_arrived_at`` column used as the
idempotency anchor for ``CrossBorderArrivedEvent`` emission when a
DobroPost shipment first reports ``status_id ∈ {648, 649}``. See
``docs/dobropost_shipment_api/integration.md``.

Note: ``provider_code = "dobropost"`` is an open string already
supported by the schema (``provider_accounts.provider_code`` and
``shipments.provider_code`` are both ``VARCHAR``); no enum migration
is required.

Revision ID: a27095efe3bc
Revises: a4f3c812d650
Create Date: 2026-04-30 01:50:32.332309

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a27095efe3bc"
down_revision: str | Sequence[str] | None = "a4f3c812d650"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "shipments",
        sa.Column(
            "cross_border_arrived_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment=(
                "First moment a cross-border shipment reported 'arrived in destination "
                "country' (DobroPost status_id ∈ {648, 649}). Idempotency anchor for "
                "CrossBorderArrivedEvent emission."
            ),
        ),
    )
    # Partial index for the "stuck cross-border" nightly job
    # (integration.md edge-case 2): finds shipments that were booked
    # > 14 days ago but never reported 648/649 — manager review.
    op.create_index(
        "ix_shipments_stuck_cross_border",
        "shipments",
        ["booked_at"],
        unique=False,
        postgresql_where=sa.text(
            "cross_border_arrived_at IS NULL "
            "AND provider_code = 'dobropost' "
            "AND status = 'booked'"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_shipments_stuck_cross_border", table_name="shipments")
    op.drop_column("shipments", "cross_border_arrived_at")
