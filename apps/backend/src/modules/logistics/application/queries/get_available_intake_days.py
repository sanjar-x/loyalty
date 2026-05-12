"""
Query handler: list days on which the provider's courier can pick up a parcel.

Wraps ``IIntakeProvider.get_available_days``.
"""

from dataclasses import dataclass

from src.modules.logistics.application.dto import GetAvailableIntakeDaysResult
from src.modules.logistics.domain.interfaces import IShippingProviderRegistry
from src.modules.logistics.domain.value_objects import Address, ProviderCode
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class GetAvailableIntakeDaysQuery:
    """Input for available-intake-days lookup.

    Attributes:
        provider_code: Logistics provider to query.
        from_address: Pickup address (used by the provider to compute its
            local working calendar).
        until: Optional upper bound (YYYY-MM-DD) on the returned window.
    """

    provider_code: ProviderCode
    from_address: Address
    until: str | None = None


class GetAvailableIntakeDaysHandler:
    """List available pickup dates for a given provider + address."""

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._registry = registry
        self._logger = logger.bind(handler="GetAvailableIntakeDaysHandler")

    async def handle(
        self, query: GetAvailableIntakeDaysQuery
    ) -> GetAvailableIntakeDaysResult:
        provider = self._registry.get_intake_provider(query.provider_code)
        windows = await provider.get_available_days(query.from_address, query.until)
        return GetAvailableIntakeDaysResult(
            provider_code=query.provider_code,
            windows=windows,
        )
