"""Read models for order queries."""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class OrderItemReadModel:
    item_id: uuid.UUID
    sku_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    product_name: str
    variant_label: str | None
    supplier_type: str
    quantity: int
    unit_price_amount: int
    currency: str
    line_total_amount: int
    cross_border_shipment_id: uuid.UUID | None
    last_mile_shipment_id: uuid.UUID | None


@dataclass(frozen=True)
class CustomerOrderReadModel:
    """Customer-facing projection — укрупнённый статус, без raw FSM значений."""

    order_id: uuid.UUID
    order_number: str
    status: str  # CustomerFacingStatus
    raw_status: str  # OrderStatus (для админских запросов из customer view опционально)
    total_amount: int
    delivery_amount: int  # kopecks; 0 для legacy/walk-in без quote
    delivery_quote_id: uuid.UUID | None
    currency: str
    pickup_carrier: str
    pickup_point_id: str
    incoming_declaration: str | None  # китайский трек (если есть)
    cross_border_tracking: str | None  # DobroPost track (после procure)
    last_mile_tracking: str | None  # russian carrier track
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemReadModel] = field(default_factory=list)


@dataclass(frozen=True)
class RecipientSnapshotReadModel:
    """Customs PII captured on the order at checkout — admin-only.

    C5.1 — surfaced on ``AdminOrderReadModel`` so the manager dashboard
    can display the customs-validation context without a cross-module
    join into the recipient table. The snapshot is the single source
    of truth for what was sent to DobroPost; the live ``Recipient``
    aggregate may have edits since.

    Frontend admin masks ``passport_serial`` / ``passport_number`` /
    ``inn`` in the UI (last 2/4 digits). Never echoed in customer-
    facing read models.
    """

    recipient_id: uuid.UUID
    full_name_ru: str
    full_name_lat: str
    phone: str
    email: str
    passport_serial: str
    passport_number: str
    passport_issue_date: date
    birth_date: date
    inn: str


@dataclass(frozen=True)
class AdminOrderReadModel:
    """Admin-facing projection — raw FSM, история, метаданные hold/cancel."""

    order_id: uuid.UUID
    order_number: str
    identity_id: uuid.UUID
    cart_id: uuid.UUID
    status: str  # raw OrderStatus
    customer_facing_status: str
    total_amount: int
    delivery_amount: int  # kopecks; 0 для legacy/walk-in без quote
    delivery_quote_id: uuid.UUID | None
    currency: str
    cny_rate_at_checkout: str | None
    pickup_carrier: str
    pickup_point_id: str
    payment_intent_id: uuid.UUID | None
    incoming_declaration: str | None
    procured_by_admin_id: uuid.UUID | None
    procured_at: datetime | None
    cross_border_shipment_id: uuid.UUID | None
    last_mile_shipment_id: uuid.UUID | None
    pre_hold_status: str | None
    hold_reason: str | None
    hold_started_at: datetime | None
    hold_until: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemReadModel] = field(default_factory=list)
    recipient_snapshot: RecipientSnapshotReadModel | None = None


@dataclass(frozen=True)
class CustomerOrderListPage:
    items: list[CustomerOrderReadModel]
    next_cursor: datetime | None


@dataclass(frozen=True)
class AdminOrderListPage:
    items: list[AdminOrderReadModel]
    next_cursor: datetime | None


@dataclass(frozen=True)
class OrderStateHistoryEntry:
    id: uuid.UUID
    from_status: str | None
    to_status: str
    event_type: str
    event_id: uuid.UUID
    actor_type: str
    actor_id: str
    metadata: dict | None
    occurred_at: datetime


@dataclass(frozen=True)
class TrackingStepReadModel:
    """One row in the customer-facing tracking timeline."""

    occurred_at: datetime
    code: str  # e.g. "order_paid", "dp:649", "rc:DELIVERED"
    label: str  # human-readable Russian description
    leg: str  # "order" | "cross_border" | "last_mile"


@dataclass(frozen=True)
class OrderTrackingReadModel:
    """Aggregated tracking view across both legs of the journey."""

    order_id: uuid.UUID
    order_number: str
    status: str  # CustomerFacingStatus
    raw_status: str
    incoming_declaration: str | None  # китайский трек
    cross_border_track: str | None  # dpTrackNumber
    last_mile_track: str | None  # russian carrier track
    cross_border_status_id: int | None  # last DobroPost status_id
    cross_border_status_label: str | None
    steps: list[TrackingStepReadModel] = field(default_factory=list)
