"""Add telegram_credentials table.

Revision ID: 20_0001
Revises: 19_0002
Create Date: 2026-03-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "20_0001"
down_revision = "19_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_credentials",
        sa.Column(
            "identity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identities.id", ondelete="CASCADE"),
            primary_key=True,
            comment="PK + FK -> identities (Shared PK 1:1)",
        ),
        sa.Column(
            "telegram_id",
            sa.BigInteger,
            unique=True,
            nullable=False,
            comment="Telegram user ID (up to 52 significant bits)",
        ),
        sa.Column(
            "first_name",
            sa.String(100),
            server_default="",
            nullable=False,
        ),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column(
            "username",
            sa.String(100),
            nullable=True,
            comment="Telegram username without @",
        ),
        sa.Column(
            "language_code",
            sa.String(10),
            nullable=True,
            comment="IETF language tag from Telegram",
        ),
        sa.Column(
            "is_premium",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
            comment="Telegram Premium subscription status",
        ),
        sa.Column(
            "photo_url",
            sa.String(512),
            nullable=True,
            comment="Telegram profile photo URL",
        ),
        sa.Column(
            "allows_write_to_pm",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
            comment="Whether user allows bot to send messages",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        comment="Telegram auth credentials (Shared PK 1:1 with identities)",
    )
    op.create_index(
        "ix_telegram_credentials_telegram_id",
        "telegram_credentials",
        ["telegram_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_telegram_credentials_telegram_id",
        table_name="telegram_credentials",
    )
    op.drop_table("telegram_credentials")
