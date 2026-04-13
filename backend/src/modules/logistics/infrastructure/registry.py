"""
Shipping provider registry — stores and retrieves provider adapters.

Each adapter implements one or more capability protocols (IRateProvider,
IBookingProvider, etc.). The registry indexes them by ProviderCode.
"""

from src.modules.logistics.domain.interfaces import (
    IBookingProvider,
    IDocumentProvider,
    IPickupPointProvider,
    IRateProvider,
    ITrackingProvider,
)
from src.modules.logistics.domain.value_objects import ProviderCode


class ShippingProviderRegistry:
    """In-memory registry of logistics provider adapters.

    Adapters are registered at application startup (APP scope via Dishka)
    and retrieved at request time by ProviderCode.
    """

    def __init__(self) -> None:
        self._rate_providers: dict[ProviderCode, IRateProvider] = {}
        self._booking_providers: dict[ProviderCode, IBookingProvider] = {}
        self._tracking_providers: dict[ProviderCode, ITrackingProvider] = {}
        self._pickup_point_providers: dict[ProviderCode, IPickupPointProvider] = {}
        self._document_providers: dict[ProviderCode, IDocumentProvider] = {}

    # -- Registration -------------------------------------------------------

    def register_rate_provider(self, provider: IRateProvider) -> None:
        self._rate_providers[provider.provider_code()] = provider

    def register_booking_provider(self, provider: IBookingProvider) -> None:
        self._booking_providers[provider.provider_code()] = provider

    def register_tracking_provider(self, provider: ITrackingProvider) -> None:
        self._tracking_providers[provider.provider_code()] = provider

    def register_pickup_point_provider(self, provider: IPickupPointProvider) -> None:
        self._pickup_point_providers[provider.provider_code()] = provider

    def register_document_provider(self, provider: IDocumentProvider) -> None:
        self._document_providers[provider.provider_code()] = provider

    # -- Retrieval ----------------------------------------------------------

    def get_rate_provider(self, code: ProviderCode) -> IRateProvider:
        try:
            return self._rate_providers[code]
        except KeyError:
            raise KeyError(f"No rate provider registered for {code.value}") from None

    def get_booking_provider(self, code: ProviderCode) -> IBookingProvider:
        try:
            return self._booking_providers[code]
        except KeyError:
            raise KeyError(f"No booking provider registered for {code.value}") from None

    def get_tracking_provider(self, code: ProviderCode) -> ITrackingProvider:
        try:
            return self._tracking_providers[code]
        except KeyError:
            raise KeyError(
                f"No tracking provider registered for {code.value}"
            ) from None

    def get_pickup_point_provider(self, code: ProviderCode) -> IPickupPointProvider:
        try:
            return self._pickup_point_providers[code]
        except KeyError:
            raise KeyError(
                f"No pickup point provider registered for {code.value}"
            ) from None

    def get_document_provider(self, code: ProviderCode) -> IDocumentProvider:
        try:
            return self._document_providers[code]
        except KeyError:
            raise KeyError(
                f"No document provider registered for {code.value}"
            ) from None

    # -- Listing ------------------------------------------------------------

    def list_rate_providers(self) -> list[IRateProvider]:
        return list(self._rate_providers.values())

    def list_pickup_point_providers(self) -> list[IPickupPointProvider]:
        return list(self._pickup_point_providers.values())

    @property
    def registered_provider_codes(self) -> set[ProviderCode]:
        """All provider codes that have at least one capability registered."""
        codes: set[ProviderCode] = set()
        for registry in (
            self._rate_providers,
            self._booking_providers,
            self._tracking_providers,
            self._pickup_point_providers,
            self._document_providers,
        ):
            codes.update(registry.keys())
        return codes
