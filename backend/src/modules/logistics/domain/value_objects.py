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
from typing import Any

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
          ↓            ↓              ↑
        CANCELLED    FAILED      (revert on
                                  cancel fail)
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
    CANCELLED = "cancelled"  # carrier-side cancellation (e.g. Yandex CANCELLED)


# Tracking statuses that imply a terminal failure of the shipment from
# the carrier's side. When ingested via webhook/polling, the Shipment
# aggregate transitions to ``ShipmentStatus.FAILED`` automatically.
TERMINAL_FAILURE_TRACKING_STATUSES: frozenset[TrackingStatus] = frozenset(
    {
        TrackingStatus.LOST,
        TrackingStatus.EXCEPTION,
    }
)

# Tracking statuses that imply a terminal cancellation of the shipment
# from the carrier's side (the carrier itself cancelled the order).
TERMINAL_CANCEL_TRACKING_STATUSES: frozenset[TrackingStatus] = frozenset(
    {
        TrackingStatus.CANCELLED,
    }
)


# ---------------------------------------------------------------------------
# Scalar value objects
# ---------------------------------------------------------------------------


@attrs.define(frozen=True)
class Weight:
    """Weight in grams."""

    grams: int

    def __attrs_post_init__(self) -> None:
        if self.grams <= 0:
            raise ValueError("Weight must be positive")


@attrs.define(frozen=True)
class Dimensions:
    """Package dimensions in centimeters."""

    length_cm: int
    width_cm: int
    height_cm: int

    def __attrs_post_init__(self) -> None:
        if self.length_cm <= 0 or self.width_cm <= 0 or self.height_cm <= 0:
            raise ValueError("All dimensions must be positive")

    @property
    def volume_cm3(self) -> int:
        return self.length_cm * self.width_cm * self.height_cm


@attrs.define(frozen=True)
class Money:
    """Monetary amount in the smallest currency unit (e.g. kopecks for RUB)."""

    amount: int
    currency_code: str  # ISO 4217

    def __attrs_post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
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
    metadata: dict[str, Any] = attrs.Factory(
        dict
    )  # e.g. {"fias_guid": "...", "cdek_city_code": 270, "cdek_order_type": "1"}


@attrs.define(frozen=True)
class ContactInfo:
    """Sender or recipient contact details with structured name fields.

    Providers require structured names (first/last/patronymic) for booking.
    Use ``full_name`` property when a single string is needed.

    ``phone`` is normalised on construction to E.164 with a leading ``+``
    and only digits afterwards (``+79529999999``). Provider adapters that
    require a different format (e.g. Yandex Delivery wants the number
    *without* the leading ``+``) strip the prefix at the mapping layer
    via the ``phone_e164_digits`` helper. This guarantees a canonical
    representation in the domain regardless of how the caller formatted
    the input (``"+7 (999) 123-45-67"``, ``"79529999999"``, etc.).
    """

    first_name: str
    last_name: str
    phone: str
    middle_name: str | None = None
    email: str | None = None
    company_name: str | None = None

    def __attrs_post_init__(self) -> None:
        normalised = _normalize_phone(self.phone)
        if normalised != self.phone:
            object.__setattr__(self, "phone", normalised)

    @property
    def full_name(self) -> str:
        """Return 'LastName FirstName MiddleName' formatted full name."""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)

    @property
    def phone_e164_digits(self) -> str:
        """Return ``phone`` without the leading ``+`` (digits only).

        Use for providers that reject the ``+`` prefix (e.g. Yandex
        Delivery requires ``79529999999`` style).
        """
        return self.phone.lstrip("+")


def _normalize_phone(raw: str) -> str:
    """Normalise a phone string to E.164 (``+`` followed by digits).

    Strips spaces, hyphens, parentheses, dots and any other formatting
    characters. If the input has no leading ``+``, one is added so
    every contact in the domain shares the same canonical form.

    Empty input is preserved (returned as ``""``) — callers decide
    whether to require a non-empty phone via Pydantic validation.
    """
    if not raw:
        return ""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return raw  # leave odd inputs alone for the caller to debug
    return f"+{digits}"


@attrs.define(frozen=True)
class ParcelItem:
    """An individual item within a parcel.

    Required for customs declarations, fiscal receipts, partial delivery,
    and provider-specific item-level tracking (CDEK items, Yandex items,
    Russian Post goods).

    Extended fields (``marking_code``, ``brand``, ``material``,
    ``name_i18n``, ``product_url``, ``cargo_types``) are mandatory in
    CDEK for **marked** product categories (jewelry → ``cargo_type=80``,
    tobacco, footwear) and for international / cross-border orders. They
    are optional for purely domestic, non-marked goods.
    """

    name: str
    quantity: int = 1
    sku: str | None = None
    unit_price: Money | None = None
    weight: Weight | None = None
    country_of_origin: str | None = None  # ISO 3166-1 alpha-2
    hs_code: str | None = None  # Harmonized System / FEACN code for customs
    # Extended (marked goods / international)
    marking_code: str | None = None  # "Честный знак" marking code
    brand: str | None = None  # required for international + marked
    material: str | None = None  # CDEK material code (Приложение 7)
    name_i18n: str | None = None  # foreign-language name (international)
    product_url: str | None = None  # link to product page
    cargo_types: tuple[str, ...] = ()  # e.g. ("80",) for jewelry

    def __attrs_post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("ParcelItem quantity must be positive")


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

    def __attrs_post_init__(self) -> None:
        if (
            self.min_days is not None
            and self.max_days is not None
            and self.min_days > self.max_days
        ):
            raise ValueError("min_days must not exceed max_days")


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
    """Result of a successful provider booking.

    ``actual_cost`` is the price the provider committed to **after** the
    order was accepted (e.g. CDEK ``delivery_detail.total_sum``). It may
    differ from the quoted price; ``BookShipmentHandler`` compares it
    against ``shipment.quoted_cost`` to detect drift.
    """

    provider_shipment_id: str
    tracking_number: str | None = None
    estimated_delivery: EstimatedDelivery | None = None
    actual_cost: Money | None = None
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


# ---------------------------------------------------------------------------
# Intake (courier pickup) value objects
# ---------------------------------------------------------------------------


class IntakeStatus(StrEnum):
    """Lifecycle status of an intake (courier pickup request)."""

    ACCEPTED = "accepted"
    WAITING = "waiting"
    DELAYED = "delayed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@attrs.define(frozen=True)
class IntakeWindow:
    """A single available date for courier intake (CDEK availableDays)."""

    date: str  # YYYY-MM-DD
    is_workday: bool = True


@attrs.define(frozen=True)
class IntakeRequest:
    """Caller input for ``IIntakeProvider.create_intake``.

    Attributes:
        order_provider_id: Provider's UUID of the linked shipment/order.
        intake_date: Target date for pickup (YYYY-MM-DD).
        intake_time_from: Earliest pickup time (HH:MM).
        intake_time_to: Latest pickup time (HH:MM).
        from_address: Pickup address.
        sender: Contact at the pickup address.
        package: Aggregated package dimensions / weight.
        comment: Free-form note for the courier.
    """

    order_provider_id: str
    intake_date: str
    intake_time_from: str
    intake_time_to: str
    from_address: Address
    sender: ContactInfo
    package: Parcel
    comment: str | None = None
    lunch_time_from: str | None = None
    lunch_time_to: str | None = None
    need_call: bool = False


@attrs.define(frozen=True)
class IntakeResult:
    """Result of a successful intake creation."""

    provider_intake_id: str
    status: IntakeStatus = IntakeStatus.UNKNOWN
    raw_response: str | None = None


# ---------------------------------------------------------------------------
# Delivery schedule value objects
# ---------------------------------------------------------------------------


@attrs.define(frozen=True)
class DeliveryInterval:
    """A single available delivery time slot."""

    start_time: str  # HH:MM
    end_time: str  # HH:MM
    date: str | None = None  # YYYY-MM-DD if known


# ---------------------------------------------------------------------------
# Returns / refusals value objects
# ---------------------------------------------------------------------------


@attrs.define(frozen=True)
class ClientReturnRequest:
    """Caller input for ``IReturnProvider.register_client_return``.

    Forms a *return* shipment from the recipient back to the sender for
    a previously delivered order. ``tariff_code`` selects the return
    tariff (CDEK Приложение 14).

    The CDEK ``POST /v2/orders/{uuid}/clientReturn`` endpoint accepts
    only ``tariff_code`` in the body — address / contact data is
    inherited from the original delivery. The remaining fields are
    kept on the VO for application-side validation and for providers
    that require richer payloads in the future.
    """

    order_provider_id: str
    tariff_code: int
    return_address: Address
    sender: ContactInfo
    recipient: ContactInfo
    parcels: list[Parcel]


@attrs.define(frozen=True)
class RefusalRequest:
    """Caller input for ``IReturnProvider.register_refusal``.

    The CDEK refusal endpoint takes no body — ``reason`` is captured
    here purely for application-side logging / audit, never sent.
    """

    order_provider_id: str
    reason: str | None = None


@attrs.define(frozen=True)
class ReturnResult:
    """Outcome of a client-return / refusal registration."""

    success: bool
    provider_return_id: str | None = None
    reason: str | None = None
    raw_response: str | None = None


@attrs.define(frozen=True)
class ReverseAvailabilityRequest:
    """Caller input for ``IReturnProvider.check_reverse_availability``.

    CDEK validates reverse availability *before* the original order is
    placed: it inspects direction (origin → destination), tariff and
    contact phones to determine whether a return path exists. Either
    ``from_location`` or ``shipment_point`` must be supplied; same for
    ``to_location`` / ``delivery_point``.
    """

    tariff_code: int
    sender_phones: tuple[str, ...]
    recipient_phones: tuple[str, ...]
    from_location: Address | None = None
    to_location: Address | None = None
    shipment_point: str | None = None
    delivery_point: str | None = None
    sender_contragent_type: str | None = None  # LEGAL_ENTITY | INDIVIDUAL
    recipient_contragent_type: str | None = None


@attrs.define(frozen=True)
class ReverseAvailabilityResult:
    """Outcome of a reverse-shipment availability check."""

    is_available: bool
    reason: str | None = None
    raw_response: str | None = None
