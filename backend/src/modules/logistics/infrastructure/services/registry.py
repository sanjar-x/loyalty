"""
Shipping provider registry — stores and retrieves provider adapters.

Each adapter implements one or more capability protocols (IRateProvider,
IBookingProvider, etc.). The registry indexes them by ProviderCode.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from src.modules.logistics.domain.exceptions import ProviderUnavailableError
from src.modules.logistics.domain.interfaces import (
    IBookingProvider,
    IDeliveryScheduleProvider,
    IDocumentProvider,
    IEditProvider,
    IIntakeProvider,
    IPickupPointProvider,
    IRateProvider,
    IReturnProvider,
    ITrackingPollProvider,
    ITrackingProvider,
    IWebhookAdapter,
)
from src.modules.logistics.domain.value_objects import ProviderCode

logger = logging.getLogger(__name__)


class ShippingProviderRegistry:
    """In-memory registry of logistics provider adapters.

    Adapters are registered at application startup (APP scope via Dishka)
    and retrieved at request time by ProviderCode.

    The registry also tracks close callbacks for the underlying HTTP
    clients held by adapter factories — call :meth:`close` at app
    shutdown to release ``httpx`` connection pools cleanly.
    """

    def __init__(self) -> None:
        self._rate_providers: dict[ProviderCode, IRateProvider] = {}
        self._booking_providers: dict[ProviderCode, IBookingProvider] = {}
        self._tracking_providers: dict[ProviderCode, ITrackingProvider] = {}
        self._tracking_poll_providers: dict[ProviderCode, ITrackingPollProvider] = {}
        self._pickup_point_providers: dict[ProviderCode, IPickupPointProvider] = {}
        self._document_providers: dict[ProviderCode, IDocumentProvider] = {}
        self._webhook_adapters: dict[ProviderCode, IWebhookAdapter] = {}
        self._intake_providers: dict[ProviderCode, IIntakeProvider] = {}
        self._delivery_schedule_providers: dict[
            ProviderCode, IDeliveryScheduleProvider
        ] = {}
        self._return_providers: dict[ProviderCode, IReturnProvider] = {}
        self._edit_providers: dict[ProviderCode, IEditProvider] = {}
        self._close_callbacks: list[Callable[[], Awaitable[None]]] = []
        # Serialises ``swap_from`` / ``reset`` so two concurrent admin
        # ``POST /refresh`` calls cannot interleave their teardowns and
        # leave dangling ``httpx.AsyncClient`` references mid-swap.
        self._swap_lock = asyncio.Lock()

    # -- Registration -------------------------------------------------------

    def register_rate_provider(self, provider: IRateProvider) -> None:
        self._rate_providers[provider.provider_code()] = provider

    def register_booking_provider(self, provider: IBookingProvider) -> None:
        self._booking_providers[provider.provider_code()] = provider

    def register_tracking_provider(self, provider: ITrackingProvider) -> None:
        self._tracking_providers[provider.provider_code()] = provider

    def register_tracking_poll_provider(self, provider: ITrackingPollProvider) -> None:
        self._tracking_poll_providers[provider.provider_code()] = provider

    def register_pickup_point_provider(self, provider: IPickupPointProvider) -> None:
        self._pickup_point_providers[provider.provider_code()] = provider

    def register_document_provider(self, provider: IDocumentProvider) -> None:
        self._document_providers[provider.provider_code()] = provider

    def register_webhook_adapter(self, adapter: IWebhookAdapter) -> None:
        self._webhook_adapters[adapter.provider_code()] = adapter

    def register_intake_provider(self, provider: IIntakeProvider) -> None:
        self._intake_providers[provider.provider_code()] = provider

    def register_delivery_schedule_provider(
        self, provider: IDeliveryScheduleProvider
    ) -> None:
        self._delivery_schedule_providers[provider.provider_code()] = provider

    def register_return_provider(self, provider: IReturnProvider) -> None:
        self._return_providers[provider.provider_code()] = provider

    def register_edit_provider(self, provider: IEditProvider) -> None:
        self._edit_providers[provider.provider_code()] = provider

    # -- Retrieval ----------------------------------------------------------

    def get_rate_provider(self, code: ProviderCode) -> IRateProvider:
        try:
            return self._rate_providers[code]
        except KeyError:
            raise ProviderUnavailableError(
                message=f"No rate provider registered for '{code}'",
                details={"provider_code": code},
            ) from None

    def get_booking_provider(self, code: ProviderCode) -> IBookingProvider:
        try:
            return self._booking_providers[code]
        except KeyError:
            raise ProviderUnavailableError(
                message=f"No booking provider registered for '{code}'",
                details={"provider_code": code},
            ) from None

    def get_tracking_provider(self, code: ProviderCode) -> ITrackingProvider:
        try:
            return self._tracking_providers[code]
        except KeyError:
            raise ProviderUnavailableError(
                message=f"No tracking provider registered for '{code}'",
                details={"provider_code": code},
            ) from None

    def get_tracking_poll_provider(self, code: ProviderCode) -> ITrackingPollProvider:
        try:
            return self._tracking_poll_providers[code]
        except KeyError:
            raise ProviderUnavailableError(
                message=f"No tracking poll provider registered for '{code}'",
                details={"provider_code": code},
            ) from None

    def get_pickup_point_provider(self, code: ProviderCode) -> IPickupPointProvider:
        try:
            return self._pickup_point_providers[code]
        except KeyError:
            raise ProviderUnavailableError(
                message=f"No pickup point provider registered for '{code}'",
                details={"provider_code": code},
            ) from None

    def get_document_provider(self, code: ProviderCode) -> IDocumentProvider:
        try:
            return self._document_providers[code]
        except KeyError:
            raise ProviderUnavailableError(
                message=f"No document provider registered for '{code}'",
                details={"provider_code": code},
            ) from None

    def get_webhook_adapter(self, code: ProviderCode) -> IWebhookAdapter:
        try:
            return self._webhook_adapters[code]
        except KeyError:
            raise ProviderUnavailableError(
                message=f"No webhook adapter registered for '{code}'",
                details={"provider_code": code},
            ) from None

    def get_intake_provider(self, code: ProviderCode) -> IIntakeProvider:
        try:
            return self._intake_providers[code]
        except KeyError:
            raise ProviderUnavailableError(
                message=f"No intake provider registered for '{code}'",
                details={"provider_code": code},
            ) from None

    def get_delivery_schedule_provider(
        self, code: ProviderCode
    ) -> IDeliveryScheduleProvider:
        try:
            return self._delivery_schedule_providers[code]
        except KeyError:
            raise ProviderUnavailableError(
                message=f"No delivery schedule provider registered for '{code}'",
                details={"provider_code": code},
            ) from None

    def get_return_provider(self, code: ProviderCode) -> IReturnProvider:
        try:
            return self._return_providers[code]
        except KeyError:
            raise ProviderUnavailableError(
                message=f"No return provider registered for '{code}'",
                details={"provider_code": code},
            ) from None

    def get_edit_provider(self, code: ProviderCode) -> IEditProvider:
        try:
            return self._edit_providers[code]
        except KeyError:
            raise ProviderUnavailableError(
                message=f"No edit provider registered for '{code}'",
                details={"provider_code": code},
            ) from None

    # -- Listing ------------------------------------------------------------

    def list_rate_providers(self) -> list[IRateProvider]:
        return list(self._rate_providers.values())

    def list_pickup_point_providers(self) -> list[IPickupPointProvider]:
        return list(self._pickup_point_providers.values())

    def list_tracking_poll_providers(self) -> list[ITrackingPollProvider]:
        return list(self._tracking_poll_providers.values())

    @property
    def registered_provider_codes(self) -> set[ProviderCode]:
        """All provider codes that have at least one capability registered."""
        codes: set[ProviderCode] = set()
        for registry in (
            self._rate_providers,
            self._booking_providers,
            self._tracking_providers,
            self._tracking_poll_providers,
            self._pickup_point_providers,
            self._document_providers,
            self._webhook_adapters,
            self._intake_providers,
            self._delivery_schedule_providers,
            self._return_providers,
            self._edit_providers,
        ):
            codes.update(registry.keys())
        return codes

    def has_webhook_adapter(self, code: ProviderCode) -> bool:
        """Check if a webhook adapter is registered for a provider."""
        return code in self._webhook_adapters

    # -- Lifecycle ----------------------------------------------------------

    def register_close_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Register an async close callback to invoke at registry shutdown.

        Used by ``bootstrap_registry`` to wire each provider factory's
        ``close()`` method into the registry's lifecycle so the Dishka
        APP-scope shutdown hook can release ``httpx`` connection pools.
        """
        self._close_callbacks.append(callback)

    async def close(self) -> None:
        """Invoke all registered close callbacks.

        Runs them sequentially — order does not matter since each
        factory owns disjoint clients. Exceptions are logged but do
        not abort sibling shutdowns: an interrupted shutdown could
        leave other clients leaked.
        """
        for callback in self._close_callbacks:
            try:
                await callback()
            except Exception:
                logger.exception("Provider close callback failed")
        self._close_callbacks.clear()

    async def reset(self) -> None:
        """Tear down every registered provider and clear all dicts.

        Equivalent to ``close()`` + clearing every capability map.
        Holds ``_swap_lock`` so a concurrent ``swap_from`` cannot race
        the close callbacks. **Avoid calling this from the admin refresh
        path** — prefer ``swap_from`` so requests in flight never see
        an empty registry. Reset is reserved for app shutdown / tests.
        """
        async with self._swap_lock:
            await self.close()
            self._clear_provider_maps()

    async def swap_from(self, other: ShippingProviderRegistry) -> None:
        """Atomically replace this registry's state with another's.

        The admin refresh path builds a fully-populated ``other`` via
        ``bootstrap_registry`` first (so any failure leaves the live
        registry untouched), then calls ``swap_from`` to install the
        new generation. Old close callbacks fire **after** the swap so
        in-flight requests that captured a provider reference can still
        complete their HTTP call before the underlying ``httpx`` pool
        is torn down.

        Note: requests that fetch a provider *after* the swap and
        *before* the old close callbacks finish will get the new
        provider — that's the intended behaviour. The narrow window
        where an in-flight request holds a now-closed client is a
        finite, recoverable error (one failed retry on the customer
        side), and is the price of in-place hot-reload without a new
        registry instance.
        """
        async with self._swap_lock:
            old_close_callbacks = self._close_callbacks
            self._rate_providers = dict(other._rate_providers)
            self._booking_providers = dict(other._booking_providers)
            self._tracking_providers = dict(other._tracking_providers)
            self._tracking_poll_providers = dict(other._tracking_poll_providers)
            self._pickup_point_providers = dict(other._pickup_point_providers)
            self._document_providers = dict(other._document_providers)
            self._webhook_adapters = dict(other._webhook_adapters)
            self._intake_providers = dict(other._intake_providers)
            self._delivery_schedule_providers = dict(other._delivery_schedule_providers)
            self._return_providers = dict(other._return_providers)
            self._edit_providers = dict(other._edit_providers)
            self._close_callbacks = list(other._close_callbacks)
            # ``other`` is consumed — its callbacks now belong to this
            # registry; clear them so the temporary instance can be
            # garbage-collected without double-closing on its __del__.
            other._close_callbacks = []
            other._clear_provider_maps()
            # Drain old generation's clients last so anything that
            # already pulled a reference can finish its in-flight call.
            for callback in old_close_callbacks:
                try:
                    await callback()
                except Exception:
                    logger.exception("Provider close callback failed during swap")

    def _clear_provider_maps(self) -> None:
        """Empty every capability map without touching close callbacks."""
        self._rate_providers.clear()
        self._booking_providers.clear()
        self._tracking_providers.clear()
        self._tracking_poll_providers.clear()
        self._pickup_point_providers.clear()
        self._document_providers.clear()
        self._webhook_adapters.clear()
        self._intake_providers.clear()
        self._delivery_schedule_providers.clear()
        self._return_providers.clear()
        self._edit_providers.clear()
