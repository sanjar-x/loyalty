"""
Query handler: calculate shipping rates across eligible providers.

Fans out rate requests to eligible providers in parallel using
asyncio.gather with graceful degradation on individual provider failures.
CQRS read side — calls provider APIs directly, then persists quotes
server-side for price integrity.
"""

import asyncio
from dataclasses import dataclass

from src.modules.logistics.application.dto import CalculateRatesResult
from src.modules.logistics.domain.exceptions import (
    NoEligibleProvidersError,
    RateCalculationError,
)
from src.modules.logistics.domain.interfaces import (
    IDeliveryQuoteRepository,
    IProviderRoutingPolicy,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import (
    Address,
    DeliveryQuote,
    Parcel,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CalculateRatesQuery:
    """Input for rate calculation.

    Attributes:
        origin: Sender address.
        destination: Recipient address.
        parcels: Packages to ship.
    """

    origin: Address
    destination: Address
    parcels: list[Parcel]


class CalculateRatesHandler:
    """Fan-out rate calculation across eligible providers.

    Providers return DeliveryQuote VOs directly (with provider_payload
    and optional expiry). We persist them server-side so that
    create-shipment can look up the trusted quote by ID.
    """

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        routing_policy: IProviderRoutingPolicy,
        quote_repo: IDeliveryQuoteRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._registry = registry
        self._routing_policy = routing_policy
        self._quote_repo = quote_repo
        self._uow = uow
        self._logger = logger.bind(handler="CalculateRatesHandler")

    async def handle(self, query: CalculateRatesQuery) -> CalculateRatesResult:
        eligible = await self._routing_policy.get_eligible_providers(
            origin=query.origin,
            destination=query.destination,
            parcels=query.parcels,
        )
        if not eligible:
            raise NoEligibleProvidersError(
                details={
                    "origin_country": query.origin.country_code,
                    "destination_country": query.destination.country_code,
                }
            )

        # Fan-out with bounded concurrency
        tasks = {}
        for code in eligible:
            provider = self._registry.get_rate_provider(code)
            tasks[code] = asyncio.create_task(
                provider.calculate_rates(
                    origin=query.origin,
                    destination=query.destination,
                    parcels=query.parcels,
                )
            )

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        quotes: list[DeliveryQuote] = []
        errors: dict[str, str] = {}

        for code, result in zip(tasks.keys(), results, strict=True):
            if isinstance(result, BaseException):
                self._logger.warning(
                    "Rate calculation failed for provider",
                    provider=code,
                    error=str(result),
                )
                errors[code] = str(result)
            else:
                quotes.extend(result)

        if not quotes and errors:
            raise RateCalculationError(details={"provider_errors": errors})

        # Persist quotes server-side for price integrity
        if quotes:
            async with self._uow:
                for quote in quotes:
                    await self._quote_repo.add(quote)
                await self._uow.commit()

        return CalculateRatesResult(quotes=quotes, errors=errors)
