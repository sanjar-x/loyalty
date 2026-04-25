"""drop_sku_main_image_url

Revision ID: b7e4a9d2c318
Revises: d8a2c31fe5b0
Create Date: 2026-04-25 13:00:00.000000

Drops the legacy denormalised ``skus.main_image_url`` column. After the
cart catalog adapter switched to LEFT JOIN on ``media_assets`` with
fallback variant-level → product-level lookup, this column has no
readers and only stored a hard-coded ``NULL`` default on every SKU
insert. Image URLs are now resolved live from ``media_assets`` (the
single source of truth, mutated by the catalog media commands), so the
denormalised cache is no longer needed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e4a9d2c318"
down_revision: str | Sequence[str] | None = "d8a2c31fe5b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("skus", "main_image_url")


def downgrade() -> None:
    op.add_column(
        "skus",
        sa.Column("main_image_url", sa.String(length=1024), nullable=True),
    )
