"""add version column to product_variants for ETag/If-Match (T-1.3 / Sprint 4)

Sprint 4 T-1.3 — same recipe as T-1.1 / T-1.2.

Revision ID: f1a2b3c4d503
Revises: f1a2b3c4d502
Create Date: 2026-05-10 06:06:24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d503"
down_revision: str | Sequence[str] | None = "f1a2b3c4d502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_variants",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment=(
                "Optimistic-locking counter (T-1.3). "
                "SQLAlchemy version_id_col bumps it on every UPDATE."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("product_variants", "version")
