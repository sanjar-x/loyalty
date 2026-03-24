"""Unified username: move to User module, add to staff_members.

Revision ID: b1c2d3e4f5a6
Revises:
Create Date: 2026-03-24
"""

import sqlalchemy as sa
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop username from local_credentials (may not exist)
    op.execute("ALTER TABLE local_credentials DROP COLUMN IF EXISTS username")

    # 2. Alter customers.username from String(100) to String(64)
    op.alter_column(
        "customers",
        "username",
        type_=sa.String(64),
        existing_type=sa.String(100),
        existing_nullable=True,
    )

    # 3. Deduplicate existing usernames (keep most recently updated)
    op.execute("""
        UPDATE customers SET username = NULL
        WHERE id NOT IN (
            SELECT DISTINCT ON (LOWER(username)) id
            FROM customers
            WHERE username IS NOT NULL
            ORDER BY LOWER(username), updated_at DESC
        )
        AND username IS NOT NULL
    """)

    # 4. Add case-insensitive UNIQUE index on customers.username
    op.create_index(
        "ix_customers_username_lower",
        "customers",
        [sa.text("LOWER(username)")],
        unique=True,
        postgresql_where=sa.text("username IS NOT NULL"),
    )

    # 5. Add username column to staff_members
    op.add_column(
        "staff_members",
        sa.Column("username", sa.String(64), nullable=True),
    )

    # 6. Add case-insensitive UNIQUE index on staff_members.username
    op.create_index(
        "ix_staff_members_username_lower",
        "staff_members",
        [sa.text("LOWER(username)")],
        unique=True,
        postgresql_where=sa.text("username IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_staff_members_username_lower", table_name="staff_members")
    op.drop_column("staff_members", "username")
    op.drop_index("ix_customers_username_lower", table_name="customers")
    op.alter_column(
        "customers",
        "username",
        type_=sa.String(100),
        existing_type=sa.String(64),
        existing_nullable=True,
    )
