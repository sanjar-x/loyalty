"""add walk-in admin orders — Order.is_walk_in, order_line_price_overrides, IdentityType.WALK_IN

Revision ID: d2e8a4f1c537
Revises: b9c3e8f4a217
Create Date: 2026-05-16 17:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d2e8a4f1c537"
down_revision: str | Sequence[str] | None = "b9c3e8f4a217"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OLD_AUTH_METHODS = ("LOCAL", "OIDC", "TELEGRAM")
_NEW_AUTH_METHODS = ("LOCAL", "OIDC", "TELEGRAM", "WALK_IN")


def upgrade() -> None:
    # --------------------------------------------------------------
    # 1) Identity.primary_auth_method — replace CHECK constraint to
    #    allow the new WALK_IN value. SQLAlchemy generates the
    #    constraint without a stable name (Enum + native_enum=False),
    #    so we locate it dynamically via pg_constraint and drop in
    #    place, then add a named replacement (ck_identities_primary_auth_method).
    # --------------------------------------------------------------
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                cname text;
            BEGIN
                SELECT con.conname INTO cname
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                WHERE rel.relname = 'identities'
                  AND con.contype = 'c'
                  AND pg_get_constraintdef(con.oid) ILIKE '%primary_auth_method%';
                IF cname IS NOT NULL THEN
                    EXECUTE format(
                        'ALTER TABLE identities DROP CONSTRAINT %I', cname
                    );
                END IF;
            END$$;
            """
        )
    )
    op.create_check_constraint(
        "primary_auth_method",
        "identities",
        "primary_auth_method IN ("
        + ", ".join(f"'{m}'" for m in _NEW_AUTH_METHODS)
        + ")",
    )

    # --------------------------------------------------------------
    # 2) orders.is_walk_in column. server_default=false so existing
    #    rows are backfilled in-place without table rewrite. The new
    #    walk-in path always sets the flag explicitly.
    # --------------------------------------------------------------
    op.add_column(
        "orders",
        sa.Column(
            "is_walk_in",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_orders_is_walk_in",
        "orders",
        ["is_walk_in"],
        unique=False,
    )

    # --------------------------------------------------------------
    # 3) order_line_price_overrides — write-once audit table for
    #    walk-in price overrides. CASCADE delete on the parent order
    #    so admin-cancelled walk-in orders stay tidy.
    # --------------------------------------------------------------
    op.create_table(
        "order_line_price_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "order_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("order_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("base_price_amount", sa.BigInteger(), nullable=False),
        sa.Column("override_price_amount", sa.BigInteger(), nullable=False),
        sa.Column("delta_amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        comment="Walk-in unit_price override audit (one row per overridden line)",
    )
    op.create_index(
        "ix_olpo_order",
        "order_line_price_overrides",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_olpo_item",
        "order_line_price_overrides",
        ["order_item_id"],
        unique=True,
    )
    op.create_index(
        "ix_olpo_admin",
        "order_line_price_overrides",
        ["admin_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_olpo_admin", table_name="order_line_price_overrides")
    op.drop_index("ix_olpo_item", table_name="order_line_price_overrides")
    op.drop_index("ix_olpo_order", table_name="order_line_price_overrides")
    op.drop_table("order_line_price_overrides")

    op.drop_index("ix_orders_is_walk_in", table_name="orders")
    op.drop_column("orders", "is_walk_in")

    # Revert CHECK to old set. Refuse if any WALK_IN rows exist —
    # downgrade is destructive in that case and must be a deliberate
    # manual step.
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM identities WHERE primary_auth_method = 'WALK_IN') "
            "THEN RAISE EXCEPTION 'Cannot downgrade: WALK_IN identities exist'; "
            "END IF; END$$;"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE identities DROP CONSTRAINT IF EXISTS "
            "ck_identities_primary_auth_method"
        )
    )
    op.create_check_constraint(
        "primary_auth_method",
        "identities",
        "primary_auth_method IN ("
        + ", ".join(f"'{m}'" for m in _OLD_AUTH_METHODS)
        + ")",
    )
