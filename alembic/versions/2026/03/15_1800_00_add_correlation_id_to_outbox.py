"""add correlation_id to outbox_messages for end-to-end tracing

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-03-15 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outbox_messages",
        sa.Column(
            "correlation_id",
            sa.String(length=64),
            nullable=True,
            comment="ID корреляции для сквозной трассировки (HTTP request_id → Outbox → TaskIQ)",
        ),
    )


def downgrade() -> None:
    op.drop_column("outbox_messages", "correlation_id")
