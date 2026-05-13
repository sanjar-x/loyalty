"""add favorites module tables

Revision ID: f2a8c1d4b913
Revises: a27095efe3bc
Create Date: 2026-05-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a8c1d4b913"
down_revision: str | Sequence[str] | None = "a27095efe3bc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create favorite_lists and favorite_items with FK + indexes."""

    op.create_table(
        "favorite_lists",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "identity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
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
        sa.CheckConstraint(
            "char_length(trim(name)) > 0",
            name="ck_favorite_lists_name_non_empty",
        ),
        comment="User-owned favorite lists (default + custom)",
    )

    op.create_index(
        "uq_favorite_lists_identity_id_name",
        "favorite_lists",
        ["identity_id", "name"],
        unique=True,
    )
    op.create_index(
        "uq_favorite_lists_identity_id_default",
        "favorite_lists",
        ["identity_id"],
        unique=True,
        postgresql_where=sa.text("is_default IS TRUE"),
    )
    op.create_index(
        "ix_favorite_lists_identity_id",
        "favorite_lists",
        ["identity_id"],
    )

    op.create_table(
        "favorite_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("favorite_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "added_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "target_type IN ('product', 'brand')",
            name="ck_favorite_items_valid_target_type",
        ),
        comment="Favorite items (products / brands) inside a list",
    )
    op.create_index(
        "uq_favorite_items_list_target",
        "favorite_items",
        ["list_id", "target_type", "target_id"],
        unique=True,
    )
    op.create_index(
        "ix_favorite_items_target",
        "favorite_items",
        ["target_type", "target_id"],
    )


def downgrade() -> None:
    """Drop favorite_items and favorite_lists in reverse order."""

    op.drop_index("ix_favorite_items_target", table_name="favorite_items")
    op.drop_index("uq_favorite_items_list_target", table_name="favorite_items")
    op.drop_table("favorite_items")

    op.drop_index("ix_favorite_lists_identity_id", table_name="favorite_lists")
    op.drop_index("uq_favorite_lists_identity_id_default", table_name="favorite_lists")
    op.drop_index("uq_favorite_lists_identity_id_name", table_name="favorite_lists")
    op.drop_table("favorite_lists")
