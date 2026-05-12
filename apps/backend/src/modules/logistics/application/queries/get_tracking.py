"""
Query handler: get tracking history for a shipment.

CQRS read side — reads from the local database (no provider call).
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import IShipmentRepository
from src.modules.logistics.domain.value_objects import TrackingEvent
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class GetTrackingQuery:
    """Input for retrieving tracking events.

    Attributes:
        shipment_id: UUID of the shipment.
    """

    shipment_id: uuid.UUID


@dataclass(frozen=True)
class GetTrackingResult:
    """Output of tracking retrieval.

    Attributes:
        shipment_id: UUID of the shipment.
        tracking_number: Provider tracking number.
        events: Chronologically ordered tracking events.
        latest_status: Most recent tracking status (or None).
    """

    shipment_id: uuid.UUID
    tracking_number: str | None
    events: list[TrackingEvent]
    latest_status: str | None


class GetTrackingHandler:
    """Read tracking history from local database."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._logger = logger.bind(handler="GetTrackingHandler")

    async def handle(self, query: GetTrackingQuery) -> GetTrackingResult:
        shipment = await self._shipment_repo.get_by_id(query.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(details={"shipment_id": str(query.shipment_id)})

        return GetTrackingResult(
            shipment_id=shipment.id,
            tracking_number=shipment.tracking_number,
            events=sorted(shipment.tracking_events, key=lambda e: e.timestamp),
            latest_status=(
                shipment.latest_tracking_status.value
                if shipment.latest_tracking_status
                else None
            ),
        )
