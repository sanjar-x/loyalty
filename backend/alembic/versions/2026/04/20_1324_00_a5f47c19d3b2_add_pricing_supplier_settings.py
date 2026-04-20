"""add_pricing_supplier_settings

Revision ID: a5f47c19d3b2
Revises: bbb88f046c3c
Create Date: 2026-04-20 13:24:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import MetaData  # noqa: F401
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a5f47c19d3b2"
down_revision: Union[str, Sequence[str], None] = "bbb88f046c3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "pricing_supplier_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("supplier_id", sa.UUID(), nullable=False),
        sa.Column(
            "values",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("version_lock", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version_lock >= 0",
            name=op.f("ck_pricing_supplier_settings_version_non_negative"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pricing_supplier_settings")),
        sa.UniqueConstraint(
            "supplier_id", name="uq_pricing_supplier_settings_supplier"
        ),
        comment="Per-supplier pricing overrides (FRD §Supplier Pricing Settings)",
    )
    op.create_index(
        op.f("ix_pricing_supplier_settings_supplier_id"),
        "pricing_supplier_settings",
        ["supplier_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_pricing_supplier_settings_supplier_id"),
        table_name="pricing_supplier_settings",
    )
    op.drop_table("pricing_supplier_settings")
