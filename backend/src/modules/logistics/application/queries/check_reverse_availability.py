"""
Query handler: ask the provider whether a return / refusal is available
for a given booked shipment.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.dto import CheckReverseAvailabilityResult
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class CheckReverseAvailabilityQuery:
    """Input for reverse-shipment availability lookup.

    Attributes:
        shipment_id: UUID of the booked shipment.
    """

    shipment_id: uuid.UUID


class CheckReverseAvailabilityHandler:
    """Ask the provider whether a return / refusal is allowed for the shipment."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._registry = registry
        self._logger = logger.bind(handler="CheckReverseAvailabilityHandler")

    async def handle(
        self, query: CheckReverseAvailabilityQuery
    ) -> CheckReverseAvailabilityResult:
        shipment = await self._shipment_repo.get_by_id(query.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(details={"shipment_id": str(query.shipment_id)})

        provider = self._registry.get_return_provider(shipment.provider_code)
        result = await provider.check_reverse_availability(
            shipment.provider_shipment_id or ""
        )
        return CheckReverseAvailabilityResult(
            shipment_id=shipment.id,
            is_available=result.is_available,
            reason=result.reason,
        )
