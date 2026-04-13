"""
Query handler: list pickup / delivery points from logistics providers.

CQRS read side — calls provider APIs directly. Supports single-provider
or fan-out across all eligible providers.
"""

import asyncio
from dataclasses import dataclass

from src.modules.logistics.domain.interfaces import IShippingProviderRegistry
from src.modules.logistics.domain.value_objects import (
    PickupPoint,
    PickupPointQuery,
    ProviderCode,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class ListPickupPointsQuery:
    """Input for listing pickup points.

    Attributes:
        query: Search criteria (location, filters, etc.).
        provider_code: If set, query only this provider; else fan-out.
    """

    query: PickupPointQuery
    provider_code: ProviderCode | None = None


@dataclass(frozen=True)
class ListPickupPointsResult:
    """Output of pickup points listing.

    Attributes:
        points: Aggregated pickup points from all queried providers.
        errors: Per-provider errors for providers that failed.
    """

    points: list[PickupPoint]
    errors: dict[str, str]


class ListPickupPointsHandler:
    """List pickup/delivery points from one or all providers."""

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._registry = registry
        self._logger = logger.bind(handler="ListPickupPointsHandler")

    async def handle(self, query: ListPickupPointsQuery) -> ListPickupPointsResult:
        if query.provider_code is not None:
            # Single provider query
            provider = self._registry.get_pickup_point_provider(query.provider_code)
            try:
                points = await provider.list_pickup_points(query.query)
            except Exception as exc:
                self._logger.warning(
                    "Pickup point listing failed",
                    provider=query.provider_code,
                    error=str(exc),
                )
                return ListPickupPointsResult(
                    points=[],
                    errors={query.provider_code: str(exc)},
                )
            return ListPickupPointsResult(points=points, errors={})

        # Fan-out across all registered providers
        providers = self._registry.list_pickup_point_providers()
        if not providers:
            return ListPickupPointsResult(points=[], errors={})

        tasks = {}
        for provider in providers:
            code = provider.provider_code()
            tasks[code] = asyncio.create_task(provider.list_pickup_points(query.query))

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        all_points: list[PickupPoint] = []
        errors: dict[str, str] = {}

        for code, result in zip(tasks.keys(), results, strict=True):
            if isinstance(result, BaseException):
                self._logger.warning(
                    "Pickup point listing failed",
                    provider=code,
                    error=str(result),
                )
                errors[code] = str(result)
            else:
                all_points.extend(result)

        return ListPickupPointsResult(points=all_points, errors=errors)
