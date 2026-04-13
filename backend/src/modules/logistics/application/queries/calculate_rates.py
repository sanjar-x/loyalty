"""
Query handler: calculate shipping rates across eligible providers.

Fans out rate requests to eligible providers in parallel using
asyncio.gather with graceful degradation on individual provider failures.
CQRS read side — calls provider APIs directly.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.logistics.application.dto import CalculateRatesResult
from src.modules.logistics.domain.exceptions import (
    NoEligibleProvidersError,
    RateCalculationError,
)
from src.modules.logistics.domain.interfaces import (
    IProviderRoutingPolicy,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import (
    Address,
    DeliveryQuote,
    Parcel,
)
from src.shared.interfaces.logger import ILogger


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
    """Fan-out rate calculation across eligible providers."""

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        routing_policy: IProviderRoutingPolicy,
        logger: ILogger,
    ) -> None:
        self._registry = registry
        self._routing_policy = routing_policy
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
        now = datetime.now(UTC)

        for code, result in zip(tasks.keys(), results, strict=True):
            if isinstance(result, BaseException):
                self._logger.warning(
                    "Rate calculation failed for provider",
                    provider=code.value,
                    error=str(result),
                )
                errors[code.value] = str(result)
            else:
                for rate in result:
                    quotes.append(
                        DeliveryQuote(
                            id=uuid.uuid4(),
                            rate=rate,
                            provider_payload="",  # provider fills during rate calc
                            quoted_at=now,
                            expires_at=None,
                        )
                    )

        if not quotes and errors:
            raise RateCalculationError(details={"provider_errors": errors})

        return CalculateRatesResult(quotes=quotes, errors=errors)
