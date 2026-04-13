"""
Logistics domain interfaces (ports).

Capability protocols for provider adapters, plus registry, routing,
webhook, polling, factory, and repository ports.
Part of the domain layer — zero framework imports.
"""

import uuid
from typing import Any, Protocol

from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.value_objects import (
    Address,
    BookingRequest,
    BookingResult,
    CancelResult,
    DeliveryQuote,
    DocumentResult,
    Parcel,
    PickupPoint,
    PickupPointQuery,
    ProviderCode,
    TrackingEvent,
)

# ---------------------------------------------------------------------------
# Capability protocols — one per logistics operation category
# ---------------------------------------------------------------------------


class IRateProvider(Protocol):
    """Calculates shipping rates / tariffs for a given route and parcels.

    Returns ``DeliveryQuote`` objects so that each provider can embed
    opaque booking data (``provider_payload``) and expiry times.
    """

    def provider_code(self) -> ProviderCode: ...

    async def calculate_rates(
        self,
        origin: Address,
        destination: Address,
        parcels: list[Parcel],
    ) -> list[DeliveryQuote]: ...


class IBookingProvider(Protocol):
    """Creates and cancels shipment bookings with a logistics provider."""

    def provider_code(self) -> ProviderCode: ...

    async def book_shipment(self, request: BookingRequest) -> BookingResult: ...

    async def cancel_shipment(self, provider_shipment_id: str) -> CancelResult: ...


class ITrackingProvider(Protocol):
    """Retrieves tracking events for a booked shipment."""

    def provider_code(self) -> ProviderCode: ...

    async def get_tracking(self, provider_shipment_id: str) -> list[TrackingEvent]: ...


class ITrackingPollProvider(Protocol):
    """Batch-polls tracking events for multiple shipments.

    Used by background sync tasks for providers without webhooks
    (e.g. Russian Post). Each provider adapter maps native statuses
    to unified ``TrackingEvent`` objects.
    """

    def provider_code(self) -> ProviderCode: ...

    async def poll_tracking_batch(
        self, provider_shipment_ids: list[str]
    ) -> dict[str, list[TrackingEvent]]: ...


class IPickupPointProvider(Protocol):
    """Lists pickup / delivery points from a logistics provider."""

    def provider_code(self) -> ProviderCode: ...

    async def list_pickup_points(
        self, query: PickupPointQuery
    ) -> list[PickupPoint]: ...


class IDocumentProvider(Protocol):
    """Generates shipping labels and documents."""

    def provider_code(self) -> ProviderCode: ...

    async def get_label(self, provider_shipment_id: str) -> DocumentResult: ...


# ---------------------------------------------------------------------------
# Webhook adapter — provider-specific payload parsing + verification
# ---------------------------------------------------------------------------


class IWebhookAdapter(Protocol):
    """Parses and verifies inbound webhooks from a logistics provider.

    Each provider has its own webhook format and signature scheme.
    The adapter validates authenticity and extracts unified tracking
    events that can be fed into ``IngestTrackingHandler``.
    """

    def provider_code(self) -> ProviderCode: ...

    async def validate_signature(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> bool:
        """Return True if the webhook payload signature is valid."""
        ...

    async def parse_events(
        self,
        body: bytes,
    ) -> list[tuple[str, list[TrackingEvent]]]:
        """Parse the webhook body into (provider_shipment_id, events) pairs.

        Returns a list of tuples, each mapping a provider shipment ID
        to the tracking events extracted from the payload. One webhook
        may carry updates for multiple shipments.
        """
        ...


# ---------------------------------------------------------------------------
# Provider factory — creates account-bound adapters from stored config
# ---------------------------------------------------------------------------


class IProviderFactory(Protocol):
    """Creates provider adapters bound to a specific account/credentials.

    Each logistics provider ships a factory that knows how to wire up
    auth managers, HTTP clients, and adapter implementations from the
    stored ``ProviderAccountConfig``.

    Not all capabilities need to be supported — unsupported ones return
    ``None``.
    """

    def provider_code(self) -> ProviderCode: ...

    def create_rate_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IRateProvider | None: ...

    def create_booking_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IBookingProvider | None: ...

    def create_tracking_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> ITrackingProvider | None: ...

    def create_tracking_poll_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> ITrackingPollProvider | None: ...

    def create_pickup_point_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IPickupPointProvider | None: ...

    def create_document_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IDocumentProvider | None: ...

    def create_webhook_adapter(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IWebhookAdapter | None: ...


# ---------------------------------------------------------------------------
# Registry — stores and retrieves provider adapters by ProviderCode
# ---------------------------------------------------------------------------


class IShippingProviderRegistry(Protocol):
    """Registry of logistics provider adapters, keyed by ProviderCode."""

    def get_rate_provider(self, code: ProviderCode) -> IRateProvider: ...

    def get_booking_provider(self, code: ProviderCode) -> IBookingProvider: ...

    def get_tracking_provider(self, code: ProviderCode) -> ITrackingProvider: ...

    def get_tracking_poll_provider(
        self, code: ProviderCode
    ) -> ITrackingPollProvider: ...

    def get_pickup_point_provider(self, code: ProviderCode) -> IPickupPointProvider: ...

    def get_document_provider(self, code: ProviderCode) -> IDocumentProvider: ...

    def get_webhook_adapter(self, code: ProviderCode) -> IWebhookAdapter: ...

    def has_webhook_adapter(self, code: ProviderCode) -> bool: ...

    def list_rate_providers(self) -> list[IRateProvider]: ...

    def list_pickup_point_providers(self) -> list[IPickupPointProvider]: ...

    def list_tracking_poll_providers(self) -> list[ITrackingPollProvider]: ...


# ---------------------------------------------------------------------------
# Routing policy — determines eligible providers for a given route
# ---------------------------------------------------------------------------


class IProviderRoutingPolicy(Protocol):
    """Determines which providers can serve a given route + parcels."""

    async def get_eligible_providers(
        self,
        origin: Address,
        destination: Address,
        parcels: list[Parcel],
    ) -> list[ProviderCode]: ...


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


class IShipmentRepository(Protocol):
    """Persistence port for Shipment aggregates."""

    async def add(self, shipment: Shipment) -> Shipment: ...

    async def get_by_id(self, shipment_id: uuid.UUID) -> Shipment | None: ...

    async def get_by_provider_shipment_id(
        self,
        provider_code: ProviderCode,
        provider_shipment_id: str,
    ) -> Shipment | None: ...

    async def update(self, shipment: Shipment) -> Shipment: ...


class IDeliveryQuoteRepository(Protocol):
    """Persistence port for server-side delivery quotes.

    Quotes are stored after rate calculation and looked up when
    creating a shipment to ensure price/payload integrity.
    """

    async def add(self, quote: DeliveryQuote) -> DeliveryQuote: ...

    async def get_by_id(self, quote_id: uuid.UUID) -> DeliveryQuote | None: ...

    async def delete_expired(self) -> int: ...
