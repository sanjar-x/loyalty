"""add order + payment modules — Loyality FSM

Revision ID: c1f2d3a4b5e6
Revises: f2a8c1d4b913
Create Date: 2026-05-02 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c1f2d3a4b5e6"
down_revision: str | Sequence[str] | None = "f2a8c1d4b913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VALID_STATUSES = (
    "'pending','paid','procured','on_hold','arrived_in_ru','in_last_mile',"
    "'awaiting_pickup','delivered','returning_to_ru_warehouse','not_delivered',"
    "'return_in_progress','returned','closed','cancelled'"
)


def upgrade() -> None:
    # ----- orders -----
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cart_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("total_amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("cny_rate_at_checkout", sa.Numeric(12, 4), nullable=True),
        sa.Column("pickup_carrier", sa.String(length=16), nullable=False),
        sa.Column("pickup_point_id", sa.String(length=128), nullable=False),
        sa.Column("payment_intent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("incoming_declaration", sa.String(length=16), nullable=True),
        sa.Column(
            "procured_by_admin_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("procured_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "cross_border_shipment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "last_mile_shipment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("cross_border_tracking", sa.String(length=64), nullable=True),
        sa.Column("last_mile_tracking", sa.String(length=64), nullable=True),
        sa.Column("pre_hold_status", sa.String(length=32), nullable=True),
        sa.Column("hold_reason", sa.String(length=32), nullable=True),
        sa.Column("hold_started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("hold_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=64), nullable=True),
        sa.Column(
            "version",
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
            f"status IN ({VALID_STATUSES})", name="ck_orders_valid_status"
        ),
        sa.CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        comment="Loyality orders — 14-state FSM",
    )
    op.create_index("ix_orders_identity_id", "orders", ["identity_id"])
    op.create_index(
        "ix_orders_identity_created",
        "orders",
        ["identity_id", "created_at"],
    )
    op.create_index("ix_orders_status_created", "orders", ["status", "created_at"])
    op.create_index("ix_orders_hold_until", "orders", ["hold_until"])
    op.create_index(
        "uix_orders_payment_intent",
        "orders",
        ["payment_intent_id"],
        unique=True,
        postgresql_where=sa.text("payment_intent_id IS NOT NULL"),
    )
    op.create_index(
        "uix_orders_incoming_declaration",
        "orders",
        ["incoming_declaration"],
        unique=True,
        postgresql_where=sa.text("incoming_declaration IS NOT NULL"),
    )
    op.create_index(
        "uix_orders_cross_border_shipment",
        "orders",
        ["cross_border_shipment_id"],
        unique=True,
        postgresql_where=sa.text("cross_border_shipment_id IS NOT NULL"),
    )
    op.create_index(
        "uix_orders_last_mile_shipment",
        "orders",
        ["last_mile_shipment_id"],
        unique=True,
        postgresql_where=sa.text("last_mile_shipment_id IS NOT NULL"),
    )

    # ----- order_items -----
    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=512), nullable=False),
        sa.Column("variant_label", sa.String(length=255), nullable=True),
        sa.Column("supplier_type", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "cross_border_shipment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "last_mile_shipment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "quantity > 0 AND quantity <= 99",
            name="ck_order_items_valid_quantity",
        ),
        sa.CheckConstraint(
            "unit_price_amount >= 0",
            name="ck_order_items_unit_price_nonnegative",
        ),
        comment="Order line items (immutable snapshots)",
    )
    op.create_index("ix_order_items_order", "order_items", ["order_id"])
    op.create_index(
        "ix_order_items_cross_border",
        "order_items",
        ["cross_border_shipment_id"],
    )
    op.create_index(
        "ix_order_items_last_mile",
        "order_items",
        ["last_mile_shipment_id"],
    )

    # ----- order_idempotency_keys -----
    op.create_table(
        "order_idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        comment="Idempotency keys for order/refund operations (TTL 24h+)",
    )
    op.create_index(
        "uix_order_idempotency_keys_key_scope",
        "order_idempotency_keys",
        ["key", "scope"],
        unique=True,
    )
    op.create_index(
        "ix_order_idempotency_keys_expires_at",
        "order_idempotency_keys",
        ["expires_at"],
    )

    # ----- order_inbox_events -----
    op.create_table(
        "order_inbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consumer", sa.String(length=64), nullable=False),
        sa.Column(
            "processed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        comment="Idempotent consumer dedup",
    )
    op.create_index(
        "uix_order_inbox_events_event_consumer",
        "order_inbox_events",
        ["event_id", "consumer"],
        unique=True,
    )

    # ----- order_state_history -----
    op.create_table(
        "order_state_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column(
            "actor_id",
            sa.String(length=128),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column("event_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        comment="Append-only Order FSM audit log",
    )
    op.create_index(
        "uix_order_state_history_event_id",
        "order_state_history",
        ["event_id"],
        unique=True,
    )
    op.create_index(
        "ix_order_state_history_order",
        "order_state_history",
        ["order_id", "occurred_at"],
    )

    # ----- payment_intents -----
    op.create_table(
        "payment_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'initiated'"),
        ),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("client_secret", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("auth_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "version",
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
            "status IN ('initiated','authorized','captured','refunded','cancelled','failed')",
            name="ck_payment_intents_valid_status",
        ),
        sa.CheckConstraint("amount > 0", name="ck_payment_intents_amount_positive"),
        comment="Payment intents (two-step authorize+capture)",
    )
    op.create_index(
        "uix_payment_intents_idempotency_key",
        "payment_intents",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index("ix_payment_intents_order", "payment_intents", ["order_id"])
    op.create_index("ix_payment_intents_status", "payment_intents", ["status"])
    op.create_index(
        "ix_payment_intents_auth_expires_at",
        "payment_intents",
        ["auth_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_intents_auth_expires_at", table_name="payment_intents")
    op.drop_index("ix_payment_intents_status", table_name="payment_intents")
    op.drop_index("ix_payment_intents_order", table_name="payment_intents")
    op.drop_index(
        "uix_payment_intents_idempotency_key",
        table_name="payment_intents",
    )
    op.drop_table("payment_intents")

    op.drop_index("ix_order_state_history_order", table_name="order_state_history")
    op.drop_index(
        "uix_order_state_history_event_id",
        table_name="order_state_history",
    )
    op.drop_table("order_state_history")

    op.drop_index(
        "uix_order_inbox_events_event_consumer",
        table_name="order_inbox_events",
    )
    op.drop_table("order_inbox_events")

    op.drop_index(
        "ix_order_idempotency_keys_expires_at",
        table_name="order_idempotency_keys",
    )
    op.drop_index(
        "uix_order_idempotency_keys_key_scope",
        table_name="order_idempotency_keys",
    )
    op.drop_table("order_idempotency_keys")

    op.drop_index("ix_order_items_last_mile", table_name="order_items")
    op.drop_index("ix_order_items_cross_border", table_name="order_items")
    op.drop_index("ix_order_items_order", table_name="order_items")
    op.drop_table("order_items")

    op.drop_index("uix_orders_last_mile_shipment", table_name="orders")
    op.drop_index("uix_orders_cross_border_shipment", table_name="orders")
    op.drop_index("uix_orders_incoming_declaration", table_name="orders")
    op.drop_index("uix_orders_payment_intent", table_name="orders")
    op.drop_index("ix_orders_hold_until", table_name="orders")
    op.drop_index("ix_orders_status_created", table_name="orders")
    op.drop_index("ix_orders_identity_created", table_name="orders")
    op.drop_index("ix_orders_identity_id", table_name="orders")
    op.drop_table("orders")
