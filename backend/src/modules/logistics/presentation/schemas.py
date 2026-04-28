"""Public API contracts for the Logistics module.

Frozen surface for the Checkout flow — the frontend builds against
these shapes and we treat changes as breaking. New optional fields are
fine; renames, type changes, and removed fields are not.

Conventions:

* JSON keys are ``snake_case`` (matches the rest of the module — cart
  uses camelCase, but logistics has historically been snake_case and
  changing it now would break the partial frontend already in flight).
* Money: integer ``amount`` in the smallest currency unit (kopecks for
  RUB) plus an ISO 4217 ``currency_code`` — never floats.
* Dates: ``date`` is ``YYYY-MM-DD`` (string), times are ``HH:MM``,
  full timestamps are RFC 3339 / ISO 8601 ``datetime``.
* Identifiers from external providers (``cdek_pvz_code``,
  ``platform_station_id``, ``fias_guid``, ``offer_id``) are *never*
  exposed; the frontend only ever sees opaque ``external_id`` and the
  server-side ``quote_id``.
* Provider / status / type fields are ``Literal[...]`` enums so the
  generated TypeScript client gets a closed union.

Versioning: any breaking change must bump the route prefix
(``/logistics/v2/...``) — this file represents v1 of the contract.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Closed enumerations — Literals so the TS client gets a union type
# ---------------------------------------------------------------------------

ProviderCodeLiteral = Literal["cdek", "yandex_delivery"]
"""Logistics providers we currently support. Adding a new provider is a
breaking change for clients that exhaustively match — bump the API."""

DeliveryTypeLiteral = Literal["courier", "pickup_point", "post_office"]
"""Mirrors ``DeliveryType`` enum in the domain layer."""

PickupPointTypeLiteral = Literal["pvz", "postamat", "post_office", "terminal"]
"""Mirrors ``PickupPointType`` enum in the domain layer."""

ShipmentStatusLiteral = Literal[
    "draft",
    "booking_pending",
    "booked",
    "cancel_pending",
    "cancelled",
    "failed",
]
"""Mirrors ``ShipmentStatus`` enum in the domain layer."""

TrackingStatusLiteral = Literal[
    "created",
    "accepted",
    "in_transit",
    "out_for_delivery",
    "ready_for_pickup",
    "delivered",
    "returned",
    "lost",
    "exception",
    "attempt_failed",
    "customs",
    "cancelled",
]
"""Mirrors ``TrackingStatus`` enum in the domain layer."""

CountryCode = str  # ISO 3166-1 alpha-2 — kept as plain str, validated by Field
CurrencyCode = str  # ISO 4217 — kept as plain str, validated by Field

# ---------------------------------------------------------------------------
# Common nested schemas
# ---------------------------------------------------------------------------


class GeoPositionSchema(BaseModel):
    """Latitude / longitude pair surfaced to the frontend map renderer."""

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class AddressSchema(BaseModel):
    """Public address shape — no provider metadata leaks here.

    Used both as request input (recipient address for courier delivery,
    edit-order destination updates) and as response output (pickup-point
    address). Provider-specific identifiers (``cdek_pvz_code``,
    ``platform_station_id``, ``fias_guid``) live on the server side and
    are *never* serialised onto this schema.
    """

    country_code: CountryCode = Field(
        ..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2"
    )
    city: str = Field(..., min_length=1)
    region: str | None = None
    postal_code: str | None = None
    street: str | None = None
    house: str | None = None
    apartment: str | None = None
    subdivision_code: str | None = Field(
        None, description="ISO 3166-2 subdivision (optional)"
    )
    raw_address: str | None = Field(
        None,
        description="Provider-formatted single-line address, when available",
    )


class ContactInfoSchema(BaseModel):
    """Sender / recipient contact details. Phone is normalised to E.164."""

    first_name: str = Field(..., min_length=1, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)
    phone: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="E.164 phone (`+79991234567`); accepted in any format and "
        "normalised server-side.",
    )
    middle_name: str | None = Field(None, max_length=128)
    email: str | None = Field(None, max_length=254)
    company_name: str | None = Field(None, max_length=255)


class WeightSchema(BaseModel):
    grams: int = Field(..., gt=0, description="Weight in grams")


class DimensionsSchema(BaseModel):
    length_cm: int = Field(..., gt=0)
    width_cm: int = Field(..., gt=0)
    height_cm: int = Field(..., gt=0)


class MoneySchema(BaseModel):
    amount: int = Field(
        ...,
        ge=0,
        description="Amount in smallest currency unit (kopecks for RUB)",
    )
    currency_code: CurrencyCode = Field(
        ..., min_length=3, max_length=3, description="ISO 4217"
    )


class CashOnDeliverySchema(BaseModel):
    amount: MoneySchema
    payment_method: Literal["cash", "card", "postpay"] | None = None


# ---------------------------------------------------------------------------
# /logistics/pickup-points — list pickup points for the storefront map
# ---------------------------------------------------------------------------


class PickupPointsRequest(BaseModel):
    """Search criteria for the map / list view.

    The frontend sends a geographic bounding box (``latitude`` +
    ``longitude`` + ``radius_km``) so the response stays bounded. ``city``
    is accepted as an alternative when geolocation is unavailable.
    Either ``(latitude AND longitude)`` or ``city`` is required — the
    handler returns 400 if neither is supplied.

    ``provider_code`` is optional: when omitted the backend fans out to
    every registered provider in parallel.
    """

    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)
    radius_km: int | None = Field(
        None, ge=1, le=100, description="Bounding-box radius in km (default 10)"
    )
    city: str | None = Field(None, min_length=1, max_length=128)
    country_code: CountryCode | None = Field(
        None, min_length=2, max_length=2, description="ISO 3166-1 alpha-2"
    )
    postal_code: str | None = None
    provider_code: ProviderCodeLiteral | None = None
    delivery_type: DeliveryTypeLiteral | None = Field(
        None,
        description="Filter by point capability (e.g. only PVZ for pickup_point)",
    )


class PickupPointSchema(BaseModel):
    """One marker on the map.

    The frontend renders ``position`` and uses ``(provider_code,
    external_id)`` as the opaque handle to pass back into
    ``/rates/quote``. Provider-internal identifiers stay on the server.
    """

    provider_code: ProviderCodeLiteral
    external_id: str = Field(
        ...,
        min_length=1,
        description="Opaque per-provider id; pass back to /rates/quote unchanged.",
    )
    name: str
    pickup_point_type: PickupPointTypeLiteral
    position: GeoPositionSchema = Field(
        ..., description="Marker coordinates — always present for map rendering"
    )
    address: AddressSchema
    work_schedule: str | None = Field(
        None,
        description="Human-readable schedule string ('Пн-Пт 10:00-21:00'), provider-specific",
    )
    phone: str | None = None
    is_cash_allowed: bool
    is_card_allowed: bool
    weight_limit_grams: int | None = Field(
        None, description="Provider-declared max parcel weight (grams)"
    )
    dimensions_limit: DimensionsSchema | None = Field(
        None, description="Provider-declared max parcel dimensions"
    )


class PickupPointsResponse(BaseModel):
    """Aggregated map response.

    ``points`` mixes both providers; the frontend differentiates them by
    ``provider_code`` (icon / colour). ``errors`` is per-provider —
    when one provider degrades the map keeps showing the other.
    """

    points: list[PickupPointSchema]
    errors: dict[ProviderCodeLiteral, str] = Field(
        default_factory=dict,
        description="provider_code → error message for providers that failed.",
    )


# ---------------------------------------------------------------------------
# /logistics/rates/quote — single quote for a chosen pickup point
# ---------------------------------------------------------------------------


class QuoteCartItemSchema(BaseModel):
    """One line in the cart at quoting time."""

    sku_id: uuid.UUID
    quantity: int = Field(1, ge=1, le=99)


class RateQuoteRequest(BaseModel):
    """Checkout-flow narrow request: SKUs + chosen pickup point.

    Backend resolves weight (from pricing category settings), origin
    warehouse (from ``ProviderAccountModel.config_json``) and the
    destination ``Address`` (from the cached pickup-point response). The
    frontend never sends weights, dimensions or destination details —
    those are server-trusted.
    """

    items: list[QuoteCartItemSchema] = Field(..., min_length=1, max_length=50)
    provider_code: ProviderCodeLiteral
    pickup_point_external_id: str = Field(
        ...,
        min_length=1,
        description=(
            "``PickupPointSchema.external_id`` from a previous "
            "/pickup-points response. Stale ids return 422."
        ),
    )
    service_code: str | None = Field(
        None,
        description=(
            "Optional explicit tariff override (e.g. 'express'). "
            "Omitting it picks the cheapest tariff returned by the provider."
        ),
    )


class RateQuoteResponse(BaseModel):
    """Single delivery quote — one line for the customer.

    ``quote_id`` is the only piece the frontend has to keep until order
    placement; price and provider details come back from the trusted
    DB-stored quote on ``/shipments`` create.
    """

    quote_id: uuid.UUID
    provider_code: ProviderCodeLiteral
    service_code: str
    service_name: str
    delivery_type: DeliveryTypeLiteral
    delivery_amount: MoneySchema = Field(
        ..., description="Customer-visible delivery cost (kopecks + currency)"
    )
    delivery_days_min: int | None = Field(None, ge=0)
    delivery_days_max: int | None = Field(None, ge=0)
    quoted_at: datetime
    expires_at: datetime = Field(
        ...,
        description=(
            "Quote becomes invalid after this moment (BRD: 30 minutes). "
            "Order placement re-checks and 409s on expiry."
        ),
    )
    fallback_alternatives: list[str] = Field(
        default_factory=list,
        description=(
            "Other ``service_code``s the provider returned for the same "
            "point — the frontend can offer them via re-quote."
        ),
    )


# ---------------------------------------------------------------------------
# /logistics/rates — full multi-provider rate listing (admin / pricing UI)
# ---------------------------------------------------------------------------


class ParcelSchema(BaseModel):
    """Used by the admin/pricing /rates endpoint where the caller knows
    real weights (e.g. after warehouse intake). The Checkout flow does
    NOT use this schema — it goes through ``/rates/quote`` instead."""

    weight: WeightSchema
    dimensions: DimensionsSchema | None = None
    declared_value: MoneySchema | None = None
    description: str | None = None


class CalculateRatesRequest(BaseModel):
    """Admin-side multi-provider rate request.

    The Checkout flow uses ``/rates/quote`` instead — this endpoint is
    kept for ops dashboards comparing tariffs across providers.
    """

    origin: AddressSchema
    destination: AddressSchema
    parcels: list[ParcelSchema] = Field(..., min_length=1)


class ShippingRateSchema(BaseModel):
    provider_code: ProviderCodeLiteral
    service_code: str
    service_name: str
    delivery_type: DeliveryTypeLiteral
    total_cost: MoneySchema
    base_cost: MoneySchema
    insurance_cost: MoneySchema | None = None
    delivery_days_min: int | None = None
    delivery_days_max: int | None = None


class DeliveryQuoteSchema(BaseModel):
    """Full quote shape used by ``/rates`` (admin endpoint)."""

    id: uuid.UUID
    rate: ShippingRateSchema
    provider_payload: str
    quoted_at: datetime
    expires_at: datetime | None = None


class CalculateRatesResponse(BaseModel):
    quotes: list[DeliveryQuoteSchema]
    errors: dict[ProviderCodeLiteral, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# /logistics/shipments — order placement
# ---------------------------------------------------------------------------


class CreateShipmentRequest(BaseModel):
    """Place a shipment from a server-side quote.

    The frontend sends only:
      * ``quote_id`` — looked up server-side; price, provider, service,
        origin, destination, parcel weight all come from the trusted
        ``DeliveryQuote`` record (BRD price-integrity).
      * ``recipient`` — buyer's contact details (typed at checkout).
      * ``order_id`` — caller-issued correlation id (cart / order id);
        echoed back on the shipment for downstream reconciliation.
      * ``cod`` — optional cash-on-delivery override; defaults to none
        (already paid online).

    The backend NEVER trusts a frontend-supplied price, weight or
    destination — those would let a tampered client place a 1-kopeck
    delivery to the wrong address. If you need to change them, request
    a new ``/rates/quote``.
    """

    quote_id: uuid.UUID = Field(
        ..., description="Result of /rates/quote within the last 30 minutes"
    )
    recipient: ContactInfoSchema
    order_id: uuid.UUID | None = Field(
        None, description="Optional caller correlation id"
    )
    cod: CashOnDeliverySchema | None = None


class ShipmentResponse(BaseModel):
    """Full shipment view."""

    id: uuid.UUID
    order_id: uuid.UUID | None
    provider_code: ProviderCodeLiteral
    service_code: str
    delivery_type: DeliveryTypeLiteral
    status: ShipmentStatusLiteral
    provider_shipment_id: str | None = None
    tracking_number: str | None = None
    quoted_cost: MoneySchema
    latest_tracking_status: TrackingStatusLiteral | None = None
    created_at: datetime
    updated_at: datetime
    booked_at: datetime | None = None
    cancelled_at: datetime | None = None


class BookShipmentResponse(BaseModel):
    shipment_id: uuid.UUID
    provider_shipment_id: str
    tracking_number: str | None = None


class CancelShipmentResponse(BaseModel):
    shipment_id: uuid.UUID


# ---------------------------------------------------------------------------
# /logistics/shipments/{id}/tracking
# ---------------------------------------------------------------------------


class TrackingEventSchema(BaseModel):
    status: TrackingStatusLiteral
    provider_status_code: str
    provider_status_name: str
    timestamp: datetime
    location: str | None = None
    description: str | None = None


class TrackingResponse(BaseModel):
    shipment_id: uuid.UUID
    tracking_number: str | None
    latest_status: TrackingStatusLiteral | None
    events: list[TrackingEventSchema]


# ---------------------------------------------------------------------------
# Intake (courier pickup) — operator UI, NOT customer-facing
# ---------------------------------------------------------------------------


class IntakeWindowSchema(BaseModel):
    date: str = Field(..., description="ISO date (YYYY-MM-DD)")
    is_workday: bool = True


IntakeStatusLiteral = Literal[
    "accepted", "waiting", "delayed", "completed", "cancelled", "unknown"
]


class AvailableIntakeDaysRequest(BaseModel):
    provider_code: ProviderCodeLiteral
    address: AddressSchema
    until: str | None = Field(None, description="Upper bound (YYYY-MM-DD)")


class AvailableIntakeDaysResponse(BaseModel):
    provider_code: ProviderCodeLiteral
    windows: list[IntakeWindowSchema]


class CreateIntakeRequest(BaseModel):
    intake_date: str = Field(..., description="Pickup date (YYYY-MM-DD)")
    intake_time_from: str = Field(..., description="Earliest time (HH:MM)")
    intake_time_to: str = Field(..., description="Latest time (HH:MM)")
    comment: str | None = None
    lunch_time_from: str | None = None
    lunch_time_to: str | None = None
    need_call: bool = False


class CreateIntakeResponse(BaseModel):
    shipment_id: uuid.UUID
    provider_intake_id: str
    status: IntakeStatusLiteral


class IntakeStatusResponse(BaseModel):
    provider_intake_id: str
    status: IntakeStatusLiteral


class CancelIntakeResponse(BaseModel):
    success: bool


# ---------------------------------------------------------------------------
# Delivery schedule — courier-only flows (operator + checkout courier mode)
# ---------------------------------------------------------------------------


class DeliveryIntervalSchema(BaseModel):
    start_time: str = Field(..., description="HH:MM")
    end_time: str = Field(..., description="HH:MM")
    date: str | None = Field(None, description="YYYY-MM-DD if known")


class DeliveryIntervalsResponse(BaseModel):
    provider_code: ProviderCodeLiteral
    intervals: list[DeliveryIntervalSchema]


class EstimatedDeliveryIntervalsRequest(BaseModel):
    provider_code: ProviderCodeLiteral
    origin: AddressSchema
    destination: AddressSchema
    tariff_code: int = Field(..., ge=1)


# ---------------------------------------------------------------------------
# Returns / refusals / reverse availability — operator UI
# ---------------------------------------------------------------------------


ContragentTypeLiteral = Literal["LEGAL_ENTITY", "INDIVIDUAL"]


class ClientReturnRequest(BaseModel):
    tariff_code: int = Field(..., ge=1)
    return_address: AddressSchema
    sender: ContactInfoSchema
    recipient: ContactInfoSchema


class RefusalRequestSchema(BaseModel):
    reason: str | None = Field(
        None, description="Free-form audit note. Not forwarded to the provider."
    )


class ReturnResponse(BaseModel):
    shipment_id: uuid.UUID
    success: bool
    provider_return_id: str | None = None
    reason: str | None = None


class ReverseAvailabilityRequestSchema(BaseModel):
    provider_code: ProviderCodeLiteral
    tariff_code: int = Field(..., ge=1)
    sender_phones: list[str] = Field(..., min_length=1, max_length=10)
    recipient_phones: list[str] = Field(..., min_length=1, max_length=10)
    from_location: AddressSchema | None = None
    to_location: AddressSchema | None = None
    shipment_point: str | None = None
    delivery_point: str | None = None
    sender_contragent_type: ContragentTypeLiteral | None = None
    recipient_contragent_type: ContragentTypeLiteral | None = None


class ReverseAvailabilityResponse(BaseModel):
    provider_code: ProviderCodeLiteral
    is_available: bool
    reason: str | None = None


# ---------------------------------------------------------------------------
# Actual delivery info (Yandex 3.05) — operator UI
# ---------------------------------------------------------------------------


class ActualDeliveryInfoSchema(BaseModel):
    delivery_date: str = Field(..., description="YYYY-MM-DD")
    interval_start: str = Field(..., description="Local HH:MM")
    interval_end: str = Field(..., description="Local HH:MM")
    timezone_offset: str | None = Field(None, description='e.g. "+03:00"')


class ActualDeliveryInfoResponse(BaseModel):
    shipment_id: uuid.UUID
    info: ActualDeliveryInfoSchema | None = None


# ---------------------------------------------------------------------------
# Edit operations (Yandex 3.06 / 3.12 / 3.13 / 3.14 / 3.15) — operator UI
# ---------------------------------------------------------------------------


EditTaskStatusLiteral = Literal["pending", "execution", "success", "failure", "unknown"]


class EditTaskResponse(BaseModel):
    shipment_id: uuid.UUID
    task_id: str
    initial_status: EditTaskStatusLiteral


class EditTaskStatusResponse(BaseModel):
    provider_code: ProviderCodeLiteral
    task_id: str
    status: EditTaskStatusLiteral


class EditPlaceSwapSchema(BaseModel):
    old_barcode: str = Field(..., min_length=1)
    new_barcode: str = Field(..., min_length=1)
    new_parcel: ParcelSchema


class EditOrderRequest(BaseModel):
    """At least one of ``recipient`` / ``destination`` / ``places`` must be set."""

    recipient: ContactInfoSchema | None = None
    destination: AddressSchema | None = None
    delivery_type: DeliveryTypeLiteral | None = None
    places: list[EditPlaceSwapSchema] = Field(default_factory=list)


class EditPackageItemSchema(BaseModel):
    item_barcode: str = Field(..., min_length=1)
    count: int = Field(..., ge=0)


class EditPackageSchema(BaseModel):
    barcode: str = Field(..., min_length=1)
    weight: WeightSchema
    dimensions: DimensionsSchema
    items: list[EditPackageItemSchema] = Field(..., min_length=1)


class EditPackagesRequest(BaseModel):
    packages: list[EditPackageSchema] = Field(..., min_length=1)


class EditItemMarkingSchema(BaseModel):
    item_barcode: str = Field(..., min_length=1)
    article: str = Field(..., min_length=1)
    marking_code: str | None = None


class EditOrderItemsRequest(BaseModel):
    items: list[EditItemMarkingSchema] = Field(..., min_length=1)


class EditItemRemovalSchema(BaseModel):
    item_barcode: str = Field(..., min_length=1)
    remaining_count: int = Field(..., ge=0, description="0 removes the item")


class RemoveOrderItemsRequest(BaseModel):
    removals: list[EditItemRemovalSchema] = Field(..., min_length=1)
