"""add supplier is_active version columns and seed marketplaces

Revision ID: c2232832f7da
Revises:
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import MetaData  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = 'c2232832f7da'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("suppliers", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("suppliers", sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False))

    # Seed marketplace suppliers (idempotent)
    marketplace_suppliers = [
        ("019550a0-0001-7000-8000-000000000001", "Poizon", "cross_border", "China"),
        ("019550a0-0002-7000-8000-000000000002", "Taobao", "cross_border", "China"),
        ("019550a0-0003-7000-8000-000000000003", "Pinduoduo", "cross_border", "China"),
        ("019550a0-0004-7000-8000-000000000004", "1688", "cross_border", "China"),
    ]
    for sid, name, stype, region in marketplace_suppliers:
        op.execute(
            sa.text(
                "INSERT INTO suppliers (id, name, type, region, is_active, version) "
                "VALUES (:id, :name, :type, :region, true, 1) "
                "ON CONFLICT (id) DO NOTHING"
            ).bindparams(id=sid, name=name, type=stype, region=region)
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove seeded data
    op.execute(sa.text(
        "DELETE FROM suppliers WHERE id IN ("
        "'019550a0-0001-7000-8000-000000000001', "
        "'019550a0-0002-7000-8000-000000000002', "
        "'019550a0-0003-7000-8000-000000000003', "
        "'019550a0-0004-7000-8000-000000000004')"
    ))
    op.drop_column("suppliers", "version")
    op.drop_column("suppliers", "is_active")
