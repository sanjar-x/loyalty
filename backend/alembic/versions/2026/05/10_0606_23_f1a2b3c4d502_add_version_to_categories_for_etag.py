"""add version column to categories for ETag/If-Match (T-1.2 / Sprint 4)

Sprint 4 T-1.2 — same recipe as T-1.1 (Brand). Optimistic-lock
counter for the Category aggregate, surfaced as ``ETag: "v{N}"``.

Revision ID: f1a2b3c4d502
Revises: f1a2b3c4d501
Create Date: 2026-05-10 06:06:23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d502"
down_revision: str | Sequence[str] | None = "f1a2b3c4d501"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment=(
                "Optimistic-locking counter (T-1.2). "
                "SQLAlchemy version_id_col bumps it on every UPDATE."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("categories", "version")
