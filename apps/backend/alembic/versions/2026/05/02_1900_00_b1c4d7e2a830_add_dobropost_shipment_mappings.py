"""add dobropost_shipment_mappings side table

Revision ID: b1c4d7e2a830
Revises: a3b5c7e9d211
Create Date: 2026-05-02 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b1c4d7e2a830"
down_revision: str | Sequence[str] | None = "a3b5c7e9d211"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dobropost_shipment_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("shipment_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dp_shipment_id", sa.BigInteger(), nullable=False),
        sa.Column("incoming_declaration", sa.String(length=32), nullable=False),
        sa.Column("dp_track_number", sa.String(length=64), nullable=True),
        sa.Column("last_status_id", sa.Integer(), nullable=True),
        sa.Column("last_status_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        comment="DobroPost int-id ↔ shipment UUID side mapping",
    )
    op.create_index(
        "uix_dpsm_dp_shipment_id",
        "dobropost_shipment_mappings",
        ["dp_shipment_id"],
        unique=True,
    )
    op.create_index(
        "uix_dpsm_shipment_uuid",
        "dobropost_shipment_mappings",
        ["shipment_uuid"],
        unique=True,
    )
    op.create_index("ix_dpsm_order", "dobropost_shipment_mappings", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_dpsm_order", table_name="dobropost_shipment_mappings")
    op.drop_index("uix_dpsm_shipment_uuid", table_name="dobropost_shipment_mappings")
    op.drop_index("uix_dpsm_dp_shipment_id", table_name="dobropost_shipment_mappings")
    op.drop_table("dobropost_shipment_mappings")
