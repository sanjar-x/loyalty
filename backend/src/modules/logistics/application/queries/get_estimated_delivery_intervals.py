"""
Query handler: estimate delivery intervals for a hypothetical shipment.

Used at checkout, *before* booking, to show the customer the slots a
courier could deliver to. Wraps ``IDeliveryScheduleProvider.get_estimated_intervals``.
"""

from dataclasses import dataclass

from src.modules.logistics.application.dto import GetDeliveryIntervalsResult
from src.modules.logistics.domain.interfaces import IShippingProviderRegistry
from src.modules.logistics.domain.value_objects import Address, ProviderCode
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class GetEstimatedDeliveryIntervalsQuery:
    """Input for pre-booking delivery-interval estimation.

    Attributes:
        provider_code: Logistics provider to query.
        origin: Sender address.
        destination: Recipient address.
        tariff_code: Provider tariff code (CDEK Приложение 1).
    """

    provider_code: ProviderCode
    origin: Address
    destination: Address
    tariff_code: int


class GetEstimatedDeliveryIntervalsHandler:
    """Estimate delivery intervals for an unbooked shipment."""

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._registry = registry
        self._logger = logger.bind(handler="GetEstimatedDeliveryIntervalsHandler")

    async def handle(
        self, query: GetEstimatedDeliveryIntervalsQuery
    ) -> GetDeliveryIntervalsResult:
        provider = self._registry.get_delivery_schedule_provider(query.provider_code)
        intervals = await provider.get_estimated_intervals(
            origin=query.origin,
            destination=query.destination,
            tariff_code=query.tariff_code,
        )
        return GetDeliveryIntervalsResult(
            provider_code=query.provider_code,
            intervals=intervals,
        )
