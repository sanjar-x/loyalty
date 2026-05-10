"""add version column to brands for ETag/If-Match (T-1.1 / Sprint 4)

Sprint 3 wired ETag/If-Match on Recipient (commit e16ca1de). Sprint 4
T-1 closes the same contract for the four catalog aggregates that
were missing a ``version`` column: Brand (this migration), Category,
ProductVariant, SKU (already had ``version`` — no DDL needed).

Strategy: monotonic optimistic-lock counter, ``version_id_col`` in
SQLAlchemy ORM. ``server_default='0'`` populates existing rows with
the lowest valid version; subsequent UPDATEs bump server-side via
``__mapper_args__``.

Revision ID: f1a2b3c4d501
Revises: e2f3a4b5c606
Create Date: 2026-05-10 06:06:22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d501"
down_revision: str | Sequence[str] | None = "e2f3a4b5c606"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "brands",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment=(
                "Optimistic-locking counter (T-1.1). "
                "SQLAlchemy version_id_col bumps it on every UPDATE."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("brands", "version")
