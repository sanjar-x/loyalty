"""
Query handler: fetch the carrier-confirmed delivery window for a shipment.

Wraps Yandex's ``GET /request/actual_info`` (3.05). CDEK adapters
return ``None`` — its actual delivery date arrives via the booking
response and is already persisted on ``Shipment.estimated_delivery``.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.dto import GetActualDeliveryInfoResult
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class GetActualDeliveryInfoQuery:
    """Input for actual delivery info lookup."""

    shipment_id: uuid.UUID


class GetActualDeliveryInfoHandler:
    """Fetch the carrier-confirmed delivery window for a shipment."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._registry = registry
        self._logger = logger.bind(handler="GetActualDeliveryInfoHandler")

    async def handle(
        self, query: GetActualDeliveryInfoQuery
    ) -> GetActualDeliveryInfoResult:
        shipment = await self._shipment_repo.get_by_id(query.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(details={"shipment_id": str(query.shipment_id)})

        provider = self._registry.get_delivery_schedule_provider(shipment.provider_code)
        info = await provider.get_actual_delivery_info(
            shipment.provider_shipment_id or ""
        )
        return GetActualDeliveryInfoResult(shipment_id=shipment.id, info=info)
