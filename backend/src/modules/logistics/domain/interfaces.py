"""
Logistics domain interfaces (ports).

Five capability protocols — a provider adapter implements whichever
capabilities it supports. Plus registry, routing, and repository ports.
Part of the domain layer — zero framework imports.
"""

import uuid
from typing import Protocol

from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.value_objects import (
    Address,
    BookingRequest,
    BookingResult,
    CancelResult,
    DocumentResult,
    Parcel,
    PickupPoint,
    PickupPointQuery,
    ProviderCode,
    ShippingRate,
    TrackingEvent,
)

# ---------------------------------------------------------------------------
# Capability protocols — one per logistics operation category
# ---------------------------------------------------------------------------


class IRateProvider(Protocol):
    """Calculates shipping rates / tariffs for a given route and parcels."""

    def provider_code(self) -> ProviderCode: ...

    async def calculate_rates(
        self,
        origin: Address,
        destination: Address,
        parcels: list[Parcel],
    ) -> list[ShippingRate]: ...


class IBookingProvider(Protocol):
    """Creates and cancels shipment bookings with a logistics provider."""

    def provider_code(self) -> ProviderCode: ...

    async def book_shipment(self, request: BookingRequest) -> BookingResult: ...

    async def cancel_shipment(self, provider_shipment_id: str) -> CancelResult: ...


class ITrackingProvider(Protocol):
    """Retrieves tracking events for a booked shipment."""

    def provider_code(self) -> ProviderCode: ...

    async def get_tracking(self, provider_shipment_id: str) -> list[TrackingEvent]: ...


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
# Registry — stores and retrieves provider adapters by ProviderCode
# ---------------------------------------------------------------------------


class IShippingProviderRegistry(Protocol):
    """Registry of logistics provider adapters, keyed by ProviderCode."""

    def get_rate_provider(self, code: ProviderCode) -> IRateProvider: ...

    def get_booking_provider(self, code: ProviderCode) -> IBookingProvider: ...

    def get_tracking_provider(self, code: ProviderCode) -> ITrackingProvider: ...

    def get_pickup_point_provider(self, code: ProviderCode) -> IPickupPointProvider: ...

    def get_document_provider(self, code: ProviderCode) -> IDocumentProvider: ...

    def list_rate_providers(self) -> list[IRateProvider]: ...

    def list_pickup_point_providers(self) -> list[IPickupPointProvider]: ...


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
# Repository
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
