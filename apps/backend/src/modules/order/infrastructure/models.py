"""ORM models for the Order bounded context — Loyality FSM (14 states)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base

VALID_STATUSES = (
    "'pending','paid','procured','on_hold','arrived_in_ru','in_last_mile',"
    "'awaiting_pickup','delivered','returning_to_ru_warehouse','not_delivered',"
    "'return_in_progress','returned','closed','cancelled'"
)


class OrderModel(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(f"status IN ({VALID_STATUSES})", name="ck_orders_valid_status"),
        CheckConstraint(
            "creation_source IN ('cart_checkout','buy_now','walk_in')",
            name="ck_orders_valid_creation_source",
        ),
        CheckConstraint(
            "(creation_source = 'walk_in') = is_walk_in",
            name="ck_orders_walk_in_source_consistent",
        ),
        # ADR-011 / Sprint 1.5 Part 2 — passport_id ⇔ passport_snapshot
        # pairing. Either both NULL (local-only order) or both set
        # (cross-border order). Cross-border vs local invariant itself
        # is enforced at the domain layer because the DB does not have
        # per-item supplier_type context (items hang off order_items).
        CheckConstraint(
            "(passport_id IS NULL) = (passport_snapshot IS NULL)",
            name="ck_orders_passport_pair_consistent",
        ),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        CheckConstraint(
            "delivery_amount >= 0", name="ck_orders_delivery_amount_nonnegative"
        ),
        Index("ix_orders_identity_created", "identity_id", "created_at"),
        Index("ix_orders_status_created", "status", "created_at"),
        Index(
            "uix_orders_payment_intent",
            "payment_intent_id",
            unique=True,
            postgresql_where="payment_intent_id IS NOT NULL",
        ),
        Index(
            "uix_orders_incoming_declaration",
            "incoming_declaration",
            unique=True,
            postgresql_where="incoming_declaration IS NOT NULL",
        ),
        Index(
            "uix_orders_cross_border_shipment",
            "cross_border_shipment_id",
            unique=True,
            postgresql_where="cross_border_shipment_id IS NOT NULL",
        ),
        Index(
            "uix_orders_last_mile_shipment",
            "last_mile_shipment_id",
            unique=True,
            postgresql_where="last_mile_shipment_id IS NOT NULL",
        ),
        Index("ix_orders_hold_until", "hold_until"),
        Index("ix_orders_recipient", "recipient_id"),
        {"comment": "Loyality orders — 14-state FSM"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    cart_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    cny_rate_at_checkout: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    pickup_carrier: Mapped[str] = mapped_column(String(16), nullable=False)
    pickup_point_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # --- recipient snapshot (immutable copy at checkout — shipping only) ---
    # Post-Sprint-1.5 Part 2 / ADR-011: customs PII columns
    # (recipient_passport_*, recipient_birth_date, recipient_inn)
    # dropped — that data lives on the new ``passport_snapshot`` JSONB
    # column further down. RecipientSnapshot here keeps only shipping
    # coordinates (name + phone + email + the soft FK to recipients.id).
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    recipient_full_name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_full_name_lat: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(16), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    payment_intent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    incoming_declaration: Mapped[str | None] = mapped_column(String(16), nullable=True)
    procured_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    procured_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    cross_border_shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    last_mile_shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    cross_border_tracking: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_mile_tracking: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pre_hold_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hold_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hold_started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    hold_until: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Shipping (REC-040). ``delivery_quote_id`` is a soft reference to
    # ``logistics.delivery_quotes`` — no FK constraint because quote
    # rows are pruned on TTL while orders are retained for years.
    # ``delivery_amount`` (kopecks, in ``currency``) is included in
    # ``total_amount`` so the payment authorization covers goods +
    # shipping in one operation. ``server_default="0"`` lets the
    # migration backfill existing rows without scanning the table.
    delivery_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    delivery_amount: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0", default=0
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Walk-in discriminator (admin-created offline order). When ``True``,
    # ``cart_id`` is a phantom UUID (no backing cart row), ``payment_intent_id``
    # may be NULL even in PAID/PROCURED states, and ``recipient_id`` does
    # not necessarily reference a Recipient row. Analytics / reconciliation
    # queries branch on this column rather than re-deriving from heuristics.
    is_walk_in: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=sa_text("false"), index=True
    )
    # BE-6 / Sprint 1.5 (2026-05-19) — Order.creation_source
    # discriminator (cart_checkout | buy_now | walk_in). Written by the
    # creating handler from the domain ``OrderCreationSource`` enum.
    # ADR-010 §I3: WALK_IN ⇔ is_walk_in=TRUE (enforced at aggregate
    # construction). Indexed for admin BI («Buy Now conversion rate»).
    creation_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=sa_text("'cart_checkout'"),
        index=True,
        comment="Order entry-point: cart_checkout | buy_now | walk_in",
    )
    # Sprint 1.5 Part 2 / ADR-011 — passport extracted as independent
    # bounded context. Order links to passport-at-checkout time:
    #
    # * ``passport_id``: soft FK to ``passports.id`` (declared in the
    #   migration with ``ON DELETE SET NULL`` so archiving a passport
    #   does not lose order history). Nullable — local-only orders
    #   skip customs entirely.
    # * ``passport_snapshot``: frozen customs PII (JSONB) for legal /
    #   reconstructable-invoice purposes. Survives Passport archival.
    #
    # Cross-border invariant (Order.create) requires both to be set
    # whenever any item has ``supplier_type=CROSS_BORDER``. DB
    # CHECK constraint enforces the same pair on persisted rows.
    passport_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    passport_snapshot: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Frozen customs PII at checkout time (full_name_ru/lat, "
            "passport_serial/number/issue_date, birth_date, inn, "
            "validation_status). Pair with passport_id; both NULL for "
            "local-only orders."
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list[OrderItemModel]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    price_overrides: Mapped[list[OrderLinePriceOverrideModel]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0 AND quantity <= 99",
            name="ck_order_items_valid_quantity",
        ),
        CheckConstraint(
            "unit_price_amount >= 0",
            name="ck_order_items_unit_price_nonnegative",
        ),
        Index("ix_order_items_order", "order_id"),
        Index("ix_order_items_cross_border", "cross_border_shipment_id"),
        Index("ix_order_items_last_mile", "last_mile_shipment_id"),
        {"comment": "Order line items (immutable snapshots)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_name: Mapped[str] = mapped_column(String(512), nullable=False)
    variant_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    cross_border_shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    last_mile_shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    order: Mapped[OrderModel] = relationship(back_populates="items")


class OrderLinePriceOverrideModel(Base):
    """Audit row recording an admin-supplied unit-price override on a walk-in line item.

    The override itself lives in ``order_items.unit_price_amount`` (single
    source of truth for invoicing). This table preserves the base price
    captured from the catalog at order-creation time + the delta + the
    admin who applied it, so reconciliation can answer "why did we charge
    X for SKU Y" months later. Rows are write-once (no UPDATE), CASCADE
    deleted when the parent order is deleted.
    """

    __tablename__ = "order_line_price_overrides"
    __table_args__ = (
        Index("ix_olpo_order", "order_id"),
        Index("ix_olpo_item", "order_item_id", unique=True),
        Index("ix_olpo_admin", "admin_id"),
        {"comment": "Walk-in unit_price override audit (one row per overridden line)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    base_price_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    override_price_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    delta_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped[OrderModel] = relationship(back_populates="price_overrides")


# OrderIdempotencyKeyModel + OrderInboxEventModel relocated to the
# framework-shared kernel (``src.infrastructure.idempotency.models``)
# per REFACT-001 PR-3a; underlying SQL tables ``order_idempotency_keys``
# and ``order_inbox_events`` are dropped by alembic revision
# ``a7d2c8f1e034`` (PR-3a) which created the shared
# ``idempotency_keys`` and ``consumer_inbox`` replacements.


class OrderStateHistoryModel(Base):
    """Audit log of every Order FSM transition (research (2) §10.2)."""

    __tablename__ = "order_state_history"
    __table_args__ = (
        Index(
            "uix_order_state_history_event_id",
            "event_id",
            unique=True,
        ),
        Index("ix_order_state_history_order", "order_id", "occurred_at"),
        {"comment": "Append-only Order FSM audit log"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class DobroPostShipmentMappingModel(Base):
    """Side mapping: DobroPost integer id ↔ our shipment UUID.

    DobroPost identifies shipments by an auto-incrementing integer, but
    Order's cross-border shipment field is a UUID (because logistics
    BCs share that abstraction). This table stores the bijection so we
    can reverse-resolve from either side without recomputing hashes.

    Webhook lookups: GET row by ``dp_shipment_id`` to find ``order_id``.
    Order ops (cancel / PUT recipient): GET row by ``order_id`` to find
    ``dp_shipment_id`` for the upstream call.
    """

    __tablename__ = "dobropost_shipment_mappings"
    __table_args__ = (
        Index(
            "uix_dpsm_dp_shipment_id",
            "dp_shipment_id",
            unique=True,
        ),
        Index(
            "uix_dpsm_shipment_uuid",
            "shipment_uuid",
            unique=True,
        ),
        Index("ix_dpsm_order", "order_id"),
        {"comment": "DobroPost int-id ↔ shipment UUID side mapping"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    shipment_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dp_shipment_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    incoming_declaration: Mapped[str] = mapped_column(String(32), nullable=False)
    dp_track_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_status_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_status_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
