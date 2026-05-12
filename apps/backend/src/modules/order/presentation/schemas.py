"""Pydantic schemas for order endpoints (camelCase aliases)."""

import uuid
from datetime import date, datetime

from pydantic import Field

from src.modules.order.domain.value_objects import (
    CancellationReason as DomainCancellationReason,
)
from src.modules.order.domain.value_objects import (
    HoldReason as DomainHoldReason,
)
from src.shared.schemas import CamelModel

# C5.2 — re-export domain enums to the presentation layer so FastAPI
# generates ``HoldReason`` / ``CancellationReason`` enum schemas in the
# OpenAPI snapshot. This replaces the prior opaque ``str`` request
# fields and gives the front-end a typed dropdown source.
HoldReason = DomainHoldReason
CancellationReason = DomainCancellationReason

# ---------------------------------------------------------------------------
# Customer-facing
# ---------------------------------------------------------------------------


class CreateOrderRequest(CamelModel):
    cart_id: uuid.UUID
    snapshot_id: uuid.UUID
    idempotency_key: str = Field(min_length=8, max_length=128)
    payment_provider: str = "fake"


class CreateOrderResponse(CamelModel):
    order_id: uuid.UUID
    payment_intent_id: uuid.UUID
    client_secret: str | None
    total_amount: int
    currency: str


class CancelOrderRequest(CamelModel):
    reason: CancellationReason = CancellationReason.CUSTOMER_CHANGED_MIND
    idempotency_key: str = Field(min_length=8, max_length=128)


class ChangePickupPointRequest(CamelModel):
    carrier: str = Field(max_length=16)
    point_id: str = Field(max_length=128)


class OrderItemSchema(CamelModel):
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


class CustomerOrderSchema(CamelModel):
    order_id: uuid.UUID
    order_number: str
    status: str
    raw_status: str
    total_amount: int
    currency: str
    pickup_carrier: str
    pickup_point_id: str
    incoming_declaration: str | None
    cross_border_tracking: str | None
    last_mile_tracking: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemSchema]


class CustomerOrderListResponse(CamelModel):
    items: list[CustomerOrderSchema]
    next_cursor: datetime | None


class TrackingStepSchema(CamelModel):
    occurred_at: datetime
    code: str
    label: str
    leg: str  # "order" | "cross_border" | "last_mile"


class OrderTrackingResponse(CamelModel):
    order_id: uuid.UUID
    order_number: str
    status: str
    raw_status: str
    incoming_declaration: str | None
    cross_border_track: str | None
    last_mile_track: str | None
    cross_border_status_id: int | None
    cross_border_status_label: str | None
    steps: list[TrackingStepSchema]


# ---------------------------------------------------------------------------
# Admin-facing
# ---------------------------------------------------------------------------


class ProcureOrderRequest(CamelModel):
    incoming_declaration: str = Field(min_length=1, max_length=15)


class HoldOrderRequest(CamelModel):
    reason: HoldReason


class RecipientSnapshotSchema(CamelModel):
    """Customs PII frozen on the order at checkout.

    C5.1 — admin-only. Frontend admin masks ``passportSerial`` /
    ``passportNumber`` / ``inn`` in the UI (last 2-4 digits). Never
    surfaced via the customer order endpoint.
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


class AdminOrderSchema(CamelModel):
    order_id: uuid.UUID
    order_number: str
    identity_id: uuid.UUID
    cart_id: uuid.UUID
    status: str
    customer_facing_status: str
    total_amount: int
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
    hold_reason: HoldReason | None
    hold_started_at: datetime | None
    hold_until: datetime | None
    cancellation_reason: CancellationReason | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemSchema]
    recipient_snapshot: RecipientSnapshotSchema | None = None


class AdminOrderListResponse(CamelModel):
    items: list[AdminOrderSchema]
    next_cursor: datetime | None


class OrderStateHistoryEntrySchema(CamelModel):
    id: uuid.UUID
    from_status: str | None
    to_status: str
    event_type: str
    event_id: uuid.UUID
    actor_type: str
    actor_id: str
    metadata: dict | None
    occurred_at: datetime


# ---------------------------------------------------------------------------
# C5.2 — taxonomy meta endpoint
# ---------------------------------------------------------------------------


class CancellationReasonGroupSchema(CamelModel):
    """One taxonomy bucket from the cancellation-reasons meta endpoint.

    The category code is one of ``customer / merchant / system /
    logistics`` (see :class:`order.domain.value_objects.CancellationCategory`);
    ``reasons`` lists every :class:`CancellationReason` that belongs to
    that category. Front-end uses this to render a grouped dropdown
    in the ForceCancelModal without hard-coding the taxonomy.
    """

    code: str
    reasons: list[CancellationReason]


class CancellationReasonsMetaResponse(CamelModel):
    """Response for ``GET /admin/orders/_meta/cancellation-reasons``."""

    categories: list[CancellationReasonGroupSchema]
