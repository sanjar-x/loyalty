"""Pydantic schemas for order endpoints (camelCase aliases)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from src.modules.order.domain.value_objects import (
    CancellationReason as DomainCancellationReason,
)
from src.modules.order.domain.value_objects import (
    HoldReason as DomainHoldReason,
)
from src.modules.order.domain.value_objects import (
    OfflinePaymentMethod as DomainOfflinePaymentMethod,
)
from src.shared.schemas import CamelModel

# C5.2 — re-export domain enums to the presentation layer so FastAPI
# generates ``HoldReason`` / ``CancellationReason`` enum schemas in the
# OpenAPI snapshot. This replaces the prior opaque ``str`` request
# fields and gives the front-end a typed dropdown source.
HoldReason = DomainHoldReason
CancellationReason = DomainCancellationReason
OfflinePaymentMethod = DomainOfflinePaymentMethod

# ---------------------------------------------------------------------------
# Customer-facing
# ---------------------------------------------------------------------------


class CreateOrderRequest(CamelModel):
    cart_id: uuid.UUID
    snapshot_id: uuid.UUID
    idempotency_key: str = Field(min_length=8, max_length=128)
    payment_provider: str = "fake"
    delivery_quote_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Server-trusted id of the quote returned by "
            "/storefront/logistics/rates/quote. When present the "
            "priced shipping amount is included in the payment "
            "authorization. Omit for orders without a priced shipping "
            "line (legacy clients)."
        ),
    )


class CreateOrderResponse(CamelModel):
    order_id: uuid.UUID
    payment_intent_id: uuid.UUID
    client_secret: str | None
    total_amount: int
    currency: str
    auto_captured: bool = Field(
        default=False,
        description=(
            "When true, the PaymentIntent was already captured server-"
            "side and the Order is already in PAID state. Frontend "
            "should skip the PSP redirect / confirmation widget and "
            "navigate straight to the order detail page. Driven by "
            "``Settings.PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE`` — true while "
            "no real PSP is wired."
        ),
    )


class BuyNowOrderRequest(CamelModel):
    """Express-checkout payload: a single SKU goes straight to Order.

    No backing cart row — front-end collects sku/quantity/recipient/
    pickup/delivery_quote in a one-shot mini-checkout sheet on the
    product page. Response shape matches :class:`CreateOrderResponse`
    so the front-end branches once on ``auto_captured``.
    """

    sku_id: uuid.UUID
    quantity: int = Field(ge=1, le=99)
    recipient_id: uuid.UUID
    pickup_carrier: str = Field(max_length=16)
    pickup_point_id: str = Field(max_length=128)
    delivery_quote_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Server-trusted id of the quote returned by "
            "/storefront/logistics/rates/quote. When present the priced "
            "shipping amount is included in the payment authorization."
        ),
    )
    idempotency_key: str = Field(min_length=8, max_length=128)
    payment_provider: str = "fake"


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
    delivery_amount: int = Field(
        default=0,
        description=(
            "Shipping line in kopecks, already included in totalAmount. "
            "0 for legacy / walk-in orders without a priced quote."
        ),
    )
    delivery_quote_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Reference to the logistics quote the customer was priced "
            "against. NULL for orders without a priced shipping line."
        ),
    )
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
    delivery_amount: int = 0
    delivery_quote_id: uuid.UUID | None = None
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


# ---------------------------------------------------------------------------
# Walk-in admin-create-order
# ---------------------------------------------------------------------------


class WalkInCustomerProfileSchema(CamelModel):
    """Minimal profile captured by admin for a walk-in customer."""

    full_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=8, max_length=16)
    email: str | None = Field(default=None, max_length=255)


class InlineRecipientSchema(CamelModel):
    """Customs PII captured inline by admin (no backing Recipient row).

    Field-level format checks live in the domain ``RecipientSnapshot``
    (passport 4+6, INN 12-digit, E.164 phone, email regex) and surface
    here as a 422 if violated.
    """

    full_name_ru: str = Field(min_length=1, max_length=255)
    full_name_lat: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=8, max_length=16)
    email: str = Field(min_length=3, max_length=255)
    passport_serial: str = Field(min_length=4, max_length=4)
    passport_number: str = Field(min_length=6, max_length=6)
    passport_issue_date: date
    birth_date: date
    inn: str = Field(min_length=12, max_length=12)


class WalkInItemSchema(CamelModel):
    """One line item of an admin-created walk-in order.

    ``unitPriceOverrideAmount`` is optional — when present and within
    the configured ratio (Settings.WALK_IN_MAX_PRICE_OVERRIDE_RATIO),
    replaces the catalog's selling_price for this line. The base price
    + delta are audited in ``order_line_price_overrides``.
    """

    sku_id: uuid.UUID
    quantity: int = Field(ge=1, le=99)
    unit_price_override_amount: int | None = Field(default=None, ge=0)
    override_reason: str | None = Field(default=None, max_length=512)


class OfflinePaymentSchema(CamelModel):
    """Anchor of an offline-captured payment (cash / bank transfer / POS)."""

    method: OfflinePaymentMethod
    reference: str = Field(min_length=1, max_length=128)
    paid_at: datetime | None = None


class AdminCreateWalkInOrderRequest(CamelModel):
    """Payload for ``POST /admin/orders`` (walk-in create)."""

    profile: WalkInCustomerProfileSchema
    recipient: InlineRecipientSchema
    items: list[WalkInItemSchema] = Field(min_length=1, max_length=50)
    pickup_carrier: str = Field(max_length=16)
    pickup_point_id: str = Field(max_length=128)
    currency: str = Field(min_length=3, max_length=3)
    payment: OfflinePaymentSchema
    idempotency_key: str = Field(min_length=8, max_length=128)
    cny_rate_at_checkout: Decimal | None = None
    delivery_amount: int = Field(default=0, ge=0)


class AdminCreateWalkInOrderResponse(CamelModel):
    order_id: uuid.UUID
    identity_id: uuid.UUID
    total_amount: int
    currency: str
