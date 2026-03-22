"""Add FK constraint from catalog.SKU.currency to geo.currencies.code.

Ensures referential integrity: SKU currency codes must exist in the
ISO 4217 currencies reference table. ON DELETE RESTRICT prevents
accidental deletion of currencies still referenced by SKUs.

Revision ID: 22_0005
Revises: 22_0004
Create Date: 2026-03-22
"""

from alembic import op

revision = "22_0005"
down_revision = "22_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add FK from skus.currency to currencies.code."""
    op.create_foreign_key(
        "fk_skus_currency_currencies",
        "skus",
        "currencies",
        ["currency"],
        ["code"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Drop FK from skus.currency."""
    op.drop_constraint("fk_skus_currency_currencies", "skus", type_="foreignkey")
