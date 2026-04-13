"""
Logistics domain value objects.

All types are frozen attrs dataclasses — immutable after construction.
Part of the domain layer — zero framework imports.

Units convention (aligned across all logistics providers):
- Weight: grams (int)
- Dimensions: centimeters (int)
- Money: smallest currency unit, e.g. kopecks for RUB (int)
"""

import uuid
from datetime import datetime
from enum import StrEnum

import attrs

# ---------------------------------------------------------------------------
# Provider identity — open string, not a closed enum
# ---------------------------------------------------------------------------

ProviderCode = str
"""Open provider identifier (e.g. ``"cdek"``, ``"yandex_delivery"``).

Any string is valid — the registry validates supported providers at
runtime.  This keeps the domain agnostic to the set of integrations.
"""


# Well-known provider codes (constants, not an enum constraint)
PROVIDER_CDEK: ProviderCode = "cdek"
PROVIDER_YANDEX_DELIVERY: ProviderCode = "yandex_delivery"
PROVIDER_RUSSIAN_POST: ProviderCode = "russian_post"


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class DeliveryType(StrEnum):
    """Delivery method categories common across all providers."""

    COURIER = "courier"
    PICKUP_POINT = "pickup_point"
    POST_OFFICE = "post_office"


class ShipmentStatus(StrEnum):
    """Local integration lifecycle states for the Shipment aggregate.

    FSM::

        DRAFT → BOOKING_PENDING → BOOKED → CANCEL_PENDING → CANCELLED
                       ↓                          ↓
                     FAILED                      FAILED
    """

    DRAFT = "draft"
    BOOKING_PENDING = "booking_pending"
    BOOKED = "booked"
    CANCEL_PENDING = "cancel_pending"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TrackingStatus(StrEnum):
    """Unified carrier tracking statuses.

    Each provider adapter maps its native statuses to these values.
    """

    CREATED = "created"
    ACCEPTED = "accepted"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    READY_FOR_PICKUP = "ready_for_pickup"
    DELIVERED = "delivered"
    RETURNED = "returned"
    LOST = "lost"
    EXCEPTION = "exception"
    ATTEMPT_FAILED = "attempt_failed"  # delivery attempt failed, will retry
    CUSTOMS = "customs"  # customs processing (international)


# ---------------------------------------------------------------------------
# Scalar value objects
# ---------------------------------------------------------------------------


@attrs.define(frozen=True)
class Weight:
    """Weight in grams."""

    grams: int

    def __attrs_post_init__(self) -> None:
        if self.grams < 0:
            raise ValueError("Weight cannot be negative")


@attrs.define(frozen=True)
class Dimensions:
    """Package dimensions in centimeters."""

    length_cm: int
    width_cm: int
    height_cm: int

    def __attrs_post_init__(self) -> None:
        if self.length_cm < 0 or self.width_cm < 0 or self.height_cm < 0:
            raise ValueError("Dimensions cannot be negative")

    @property
    def volume_cm3(self) -> int:
        return self.length_cm * self.width_cm * self.height_cm


@attrs.define(frozen=True)
class Money:
    """Monetary amount in the smallest currency unit (e.g. kopecks for RUB)."""

    amount: int
    currency_code: str  # ISO 4217

    def __attrs_post_init__(self) -> None:
        if not self.currency_code:
            raise ValueError("Currency code is required")


# ---------------------------------------------------------------------------
# Composite value objects
# ---------------------------------------------------------------------------


@attrs.define(frozen=True)
class Address:
    """Shipping address with optional geocoordinates.

    References geo module concepts (country_code, subdivision_code)
    but is self-contained within the logistics domain.

    ``metadata`` carries provider- or country-specific address
    references (FIAS GUID, KLADR code, CDEK city code, etc.)
    without polluting the core VO with provider-specific fields.
    """

    country_code: str  # ISO 3166-1 alpha-2
    city: str
    region: str | None = None  # human-readable region / oblast / krai
    postal_code: str | None = None
    street: str | None = None
    house: str | None = None
    apartment: str | None = None
    subdivision_code: str | None = None  # ISO 3166-2
    latitude: float | None = None
    longitude: float | None = None
    raw_address: str | None = None  # provider-formatted full address
    metadata: dict[str, str] = attrs.Factory(dict)  # e.g. {"fias_guid": "...", "cdek_city_code": "..."}


@attrs.define(frozen=True)
class ContactInfo:
    """Sender or recipient contact details with structured name fields.

    Providers require structured names (first/last/patronymic) for booking.
    Use ``full_name`` property when a single string is needed.
    """

    first_name: str
    last_name: str
    phone: str
    middle_name: str | None = None
    email: str | None = None
    company_name: str | None = None

    @property
    def full_name(self) -> str:
        """Return 'LastName FirstName MiddleName' formatted full name."""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)


@attrs.define(frozen=True)
class ParcelItem:
    """An individual item within a parcel.

    Required for customs declarations, fiscal receipts, partial delivery,
    and provider-specific item-level tracking (CDEK items, Yandex items,
    Russian Post goods).
    """

    name: str
    quantity: int = 1
    sku: str | None = None
    unit_price: Money | None = None
    weight: Weight | None = None
    country_of_origin: str | None = None  # ISO 3166-1 alpha-2
    hs_code: str | None = None  # Harmonized System code for customs


@attrs.define(frozen=True)
class Parcel:
    """A single package in a shipment."""

    weight: Weight
    dimensions: Dimensions | None = None
    declared_value: Money | None = None
    description: str | None = None
    items: list[ParcelItem] = attrs.Factory(list)


# ---------------------------------------------------------------------------
# Rate / quote value objects
# ---------------------------------------------------------------------------


@attrs.define(frozen=True)
class ShippingRate:
    """Single tariff option returned by a provider."""

    provider_code: ProviderCode
    service_code: str
    service_name: str
    delivery_type: DeliveryType
    total_cost: Money
    base_cost: Money
    insurance_cost: Money | None = None
    delivery_days_min: int | None = None
    delivery_days_max: int | None = None


@attrs.define(frozen=True)
class DeliveryQuote:
    """Bridging value object: a selected rate + opaque provider data for booking.

    The ``provider_payload`` carries serialised provider-specific data
    (e.g. an offer ID or tariff token) that the booking adapter needs.
    """

    id: uuid.UUID
    rate: ShippingRate
    provider_payload: str  # JSON-serialised opaque data
    quoted_at: datetime
    expires_at: datetime | None = None


@attrs.define(frozen=True)
class CashOnDelivery:
    """Cash on delivery (COD) / payment on delivery configuration."""

    amount: Money
    payment_method: str | None = None  # e.g. "cash", "card", "postpay"


@attrs.define(frozen=True)
class EstimatedDelivery:
    """Estimated delivery window returned by provider after booking."""

    min_days: int | None = None
    max_days: int | None = None
    estimated_date: datetime | None = None


# ---------------------------------------------------------------------------
# Tracking value objects
# ---------------------------------------------------------------------------


@attrs.define(frozen=True)
class TrackingEvent:
    """A single status transition reported by a carrier."""

    status: TrackingStatus
    provider_status_code: str
    provider_status_name: str
    timestamp: datetime
    location: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# Pickup point value objects
# ---------------------------------------------------------------------------


class PickupPointType(StrEnum):
    """Type of pickup / delivery point."""

    PVZ = "pvz"
    POSTAMAT = "postamat"
    POST_OFFICE = "post_office"
    TERMINAL = "terminal"


@attrs.define(frozen=True)
class PickupPoint:
    """A pickup / delivery point from a logistics provider."""

    provider_code: ProviderCode
    external_id: str
    name: str
    pickup_point_type: PickupPointType
    address: Address
    work_schedule: str | None = None
    phone: str | None = None
    is_cash_allowed: bool = False
    is_card_allowed: bool = False
    weight_limit_grams: int | None = None
    dimensions_limit: Dimensions | None = None


@attrs.define(frozen=True)
class PickupPointQuery:
    """Search criteria for listing pickup points."""

    country_code: str | None = None
    city: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_km: int | None = None
    provider_code: ProviderCode | None = None
    delivery_type: DeliveryType | None = None


# ---------------------------------------------------------------------------
# Provider interaction DTOs (used in capability interfaces)
# ---------------------------------------------------------------------------


@attrs.define(frozen=True)
class BookingRequest:
    """Data needed by ``IBookingProvider.book_shipment()``."""

    shipment_id: uuid.UUID
    origin: Address
    destination: Address
    sender: ContactInfo
    recipient: ContactInfo
    parcels: list[Parcel]
    service_code: str
    delivery_type: DeliveryType
    provider_payload: str  # opaque data from DeliveryQuote
    declared_value: Money | None = None
    cod: CashOnDelivery | None = None


@attrs.define(frozen=True)
class BookingResult:
    """Result of a successful provider booking."""

    provider_shipment_id: str
    tracking_number: str | None = None
    estimated_delivery: EstimatedDelivery | None = None
    provider_response_payload: str | None = None  # raw JSON for audit


@attrs.define(frozen=True)
class CancelResult:
    """Result of a shipment cancellation request."""

    success: bool
    reason: str | None = None


@attrs.define(frozen=True)
class DocumentResult:
    """Reference to a generated shipping label / document."""

    document_url: str | None = None
    document_bytes: bytes | None = None
    content_type: str = "application/pdf"
