"""Refresh service for the in-memory ``ShippingProviderRegistry``.

Lives in the infrastructure layer because the operation is pure
plumbing: build a fresh ``ShippingProviderRegistry`` from the current
``provider_accounts`` rows, then atomically swap it into the live
APP-scoped registry. There is no business rule, no domain event, no
aggregate state — so a free-standing infrastructure service is a
better fit than an application/command handler (which would also
violate the Clean Architecture boundary between application and
infrastructure).

Used by the admin REST refresh endpoint and exposed via Dishka so
the router can inject it without depending on infrastructure modules
directly.

Build-then-swap rationale: an earlier version of this service did
``registry.reset()`` *before* re-bootstrapping. That left the live
registry empty for the duration of the rebuild, which (a) failed
in-flight customer requests with ``ProviderUnavailableError``, and
(b) on a partial bootstrap failure left the registry partially
populated and indistinguishable from a healthy degraded state.
``swap_from`` keeps the old generation serving traffic until the new
one is fully assembled, and a failed bootstrap raises with the live
registry untouched.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.logistics.domain.interfaces import IShippingProviderRegistry
from src.modules.logistics.domain.value_objects import ProviderCode
from src.modules.logistics.infrastructure.bootstrap import bootstrap_registry
from src.modules.logistics.infrastructure.services.registry import (
    ShippingProviderRegistry,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class RegistryRefreshResult:
    registered_provider_codes: list[ProviderCode]


class ProviderRegistryRefresher:
    """Build a fresh registry from DB and atomically swap it into the live one.

    Caveats — surfaced explicitly in the admin UX:

    * Multi-worker deploys: each worker holds its own registry instance
      (Dishka APP scope). One refresh request only updates the worker
      that served it — operators must roll the rest manually.
    * Failures during build leave the live registry untouched: errors
      bubble up before any swap takes place.
    """

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        session_factory: async_sessionmaker[AsyncSession],
        logger: ILogger,
    ) -> None:
        # ``swap_from`` is a concrete-class operation; narrow once at
        # construction time so the call site doesn't have to chase
        # the cast. The interface widening to ``reset`` /
        # ``registered_provider_codes`` keeps consumers decoupled,
        # but a swap mutates two concrete instances and is naturally
        # bound to the implementation.
        if not isinstance(registry, ShippingProviderRegistry):
            raise TypeError(
                "ProviderRegistryRefresher requires the concrete "
                "ShippingProviderRegistry instance"
            )
        self._registry = registry
        self._session_factory = session_factory
        self._logger = logger.bind(service="ProviderRegistryRefresher")

    async def refresh(self) -> RegistryRefreshResult:
        # Build the new generation in a brand-new registry. If
        # ``bootstrap_registry`` raises (DB outage, malformed
        # credentials_json on a row, factory ctor blowing up), the
        # live registry is untouched and the admin sees a clean error.
        new_registry = ShippingProviderRegistry()
        try:
            await bootstrap_registry(self._session_factory, registry=new_registry)
        except Exception:
            # Drop any partially-built clients so we don't leak ``httpx``
            # pools from the failed attempt before re-raising.
            await new_registry.reset()
            raise

        await self._registry.swap_from(new_registry)
        codes = sorted(self._registry.registered_provider_codes)
        self._logger.info("Provider registry refreshed", registered=codes)
        return RegistryRefreshResult(registered_provider_codes=codes)
