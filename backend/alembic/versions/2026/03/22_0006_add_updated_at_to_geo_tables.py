"""Add updated_at column to geo reference tables.

Provides minimal audit trail for reference data changes.
Countries, currencies, and languages now track last modification time.

Revision ID: 22_0006
Revises: 22_0005
Create Date: 2026-03-22
"""

import sqlalchemy as sa
from sqlalchemy.sql import func

from alembic import op

revision = "22_0006"
down_revision = "22_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add updated_at to countries, currencies, languages."""
    for table in ("countries", "currencies", "languages"):
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=func.now(),
                nullable=False,
                comment="Last modification timestamp",
            ),
        )


def downgrade() -> None:
    """Drop updated_at from countries, currencies, languages."""
    for table in ("countries", "currencies", "languages"):
        op.drop_column(table, "updated_at")
