"""
Query handler: get a single shipment by ID.

CQRS read side — reads from the local database.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import IShipmentRepository
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class GetShipmentQuery:
    """Input for retrieving a single shipment.

    Attributes:
        shipment_id: UUID of the shipment.
    """

    shipment_id: uuid.UUID


class GetShipmentHandler:
    """Retrieve a shipment by ID."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._logger = logger.bind(handler="GetShipmentHandler")

    async def handle(self, query: GetShipmentQuery) -> Shipment:
        shipment = await self._shipment_repo.get_by_id(query.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(details={"shipment_id": str(query.shipment_id)})
        return shipment
