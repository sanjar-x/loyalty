"""Drop telegram_credentials table (post-deploy verification).

Revision ID: 20_0003
Revises: 20_0002
Create Date: 2026-03-20
"""

from alembic import op

revision = "20_0003"
down_revision = "20_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("telegram_credentials")


def downgrade() -> None:
    raise NotImplementedError("Cannot reverse telegram_credentials drop. Restore from backup.")
