"""add outbox_messages table for transactional outbox

Revision ID: a1b2c3d4e5f6
Revises: 9108a4a20a82
Create Date: 2026-03-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "9108a4a20a82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox_messages",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            comment="PK (UUIDv4, т.к. uuid7 опционален)",
        ),
        sa.Column(
            "aggregate_type",
            sa.String(length=255),
            nullable=False,
            comment="Тип агрегата-источника (Brand, Order, ...)",
        ),
        sa.Column(
            "aggregate_id",
            sa.String(length=255),
            nullable=False,
            comment="ID агрегата-источника",
        ),
        sa.Column(
            "event_type",
            sa.String(length=255),
            nullable=False,
            comment="Название доменного события (BrandLogoConfirmedEvent, ...)",
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Сериализованное тело события (.model_dump(mode='json'))",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Момент записи события в Outbox",
        ),
        sa.Column(
            "processed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Момент успешной публикации в брокер (NULL = не обработано)",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_messages")),
    )
    # Критический индекс для Relay-воркера:
    # WHERE processed_at IS NULL ORDER BY created_at ASC
    op.create_index(
        "ix_outbox_processed_created",
        "outbox_messages",
        ["processed_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_processed_created", table_name="outbox_messages")
    op.drop_table("outbox_messages")
