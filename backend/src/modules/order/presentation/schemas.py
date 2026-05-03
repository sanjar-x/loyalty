"""Pydantic schemas for order endpoints (camelCase aliases)."""

import uuid
from datetime import datetime

from pydantic import Field

from src.shared.schemas import CamelModel

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
    reason: str = Field(default="customer_changed_mind", max_length=64)
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
    reason: str = Field(max_length=32)


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
    hold_reason: str | None
    hold_started_at: datetime | None
    hold_until: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemSchema]


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
