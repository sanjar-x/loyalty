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
# Enumerations
# ---------------------------------------------------------------------------


class ProviderCode(StrEnum):
    """Known logistics provider identifiers.

    Extensible: add new providers as they are integrated.
    """

    CDEK = "cdek"
    YANDEX_DELIVERY = "yandex_delivery"
    RUSSIAN_POST = "russian_post"


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
    """

    country_code: str  # ISO 3166-1 alpha-2
    city: str
    postal_code: str | None = None
    street: str | None = None
    house: str | None = None
    apartment: str | None = None
    subdivision_code: str | None = None  # ISO 3166-2
    latitude: float | None = None
    longitude: float | None = None
    raw_address: str | None = None  # provider-formatted full address


@attrs.define(frozen=True)
class ContactInfo:
    """Sender or recipient contact details."""

    full_name: str
    phone: str
    email: str | None = None


@attrs.define(frozen=True)
class Parcel:
    """A single package in a shipment."""

    weight: Weight
    dimensions: Dimensions | None = None
    declared_value: Money | None = None
    description: str | None = None


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


@attrs.define(frozen=True)
class PickupPoint:
    """A pickup / delivery point from a logistics provider."""

    provider_code: ProviderCode
    external_id: str
    name: str
    pickup_point_type: str  # PVZ, POSTAMAT, TERMINAL, POST_OFFICE
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
    recipient: ContactInfo
    parcels: list[Parcel]
    service_code: str
    delivery_type: DeliveryType
    provider_payload: str  # opaque data from DeliveryQuote
    declared_value: Money | None = None


@attrs.define(frozen=True)
class BookingResult:
    """Result of a successful provider booking."""

    provider_shipment_id: str
    tracking_number: str | None = None
    estimated_delivery_date: datetime | None = None
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


@attrs.define(frozen=True)
class ProviderClientConfig:
    """HTTP client configuration for a logistics provider."""

    base_url: str
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_base_delay: float = 1.0
