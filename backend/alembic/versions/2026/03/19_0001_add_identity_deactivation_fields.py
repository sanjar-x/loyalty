"""Add deactivation tracking fields to identities table.

Revision ID: 19_0001
Revises: d2bb038b00e3
Create Date: 2026-03-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from alembic import op

revision = "19_0001"
down_revision = "d2bb038b00e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "identities",
        sa.Column("deactivated_at", TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "identities",
        sa.Column("deactivated_by", UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("identities", "deactivated_by")
    op.drop_column("identities", "deactivated_at")
