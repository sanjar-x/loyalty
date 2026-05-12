"""
Query handler: list available delivery intervals for a booked shipment.

Wraps ``IDeliveryScheduleProvider.get_intervals``.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.dto import GetDeliveryIntervalsResult
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class GetDeliveryIntervalsQuery:
    """Input for delivery-interval lookup of a booked shipment.

    Attributes:
        shipment_id: UUID of the booked shipment.
    """

    shipment_id: uuid.UUID


class GetDeliveryIntervalsHandler:
    """Fetch available delivery intervals for a booked shipment."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._registry = registry
        self._logger = logger.bind(handler="GetDeliveryIntervalsHandler")

    async def handle(
        self, query: GetDeliveryIntervalsQuery
    ) -> GetDeliveryIntervalsResult:
        shipment = await self._shipment_repo.get_by_id(query.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(details={"shipment_id": str(query.shipment_id)})

        provider = self._registry.get_delivery_schedule_provider(shipment.provider_code)
        intervals = await provider.get_intervals(shipment.provider_shipment_id or "")
        return GetDeliveryIntervalsResult(
            provider_code=shipment.provider_code,
            intervals=intervals,
        )
