"""
Command handler: ingest tracking updates (from webhook or polling).

Unified ingestion path — both webhook adapters and polling tasks
call this handler. Deduplication is handled by the Shipment aggregate.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import IShipmentRepository
from src.modules.logistics.domain.value_objects import (
    ProviderCode,
    TrackingEvent,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class IngestTrackingCommand:
    """Input for ingesting tracking events.

    Attributes:
        provider_code: Which provider sent the update.
        provider_shipment_id: Provider's shipment identifier.
        events: New tracking events to ingest.
        raw_payload: Original provider payload for audit (optional).
    """

    provider_code: ProviderCode
    provider_shipment_id: str
    events: list[TrackingEvent]
    raw_payload: str | None = None


@dataclass(frozen=True)
class IngestTrackingResult:
    """Output of tracking ingestion.

    Attributes:
        shipment_id: UUID of the updated shipment.
        new_events_count: Number of genuinely new events (after dedup).
    """

    shipment_id: uuid.UUID
    new_events_count: int


class IngestTrackingHandler:
    """Ingest carrier tracking events into a Shipment aggregate.

    Idempotent — duplicate events (same timestamp + status) are silently ignored.
    """

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._uow = uow
        self._logger = logger.bind(handler="IngestTrackingHandler")

    async def handle(self, command: IngestTrackingCommand) -> IngestTrackingResult:
        async with self._uow:
            shipment = await self._shipment_repo.get_by_provider_shipment_id(
                provider_code=command.provider_code,
                provider_shipment_id=command.provider_shipment_id,
            )
            if shipment is None:
                raise ShipmentNotFoundError(
                    details={
                        "provider_code": command.provider_code.value,
                        "provider_shipment_id": command.provider_shipment_id,
                    }
                )

            events_before = len(shipment.tracking_events)
            for event in command.events:
                shipment.append_tracking_event(event)
            new_count = len(shipment.tracking_events) - events_before

            if new_count > 0:
                shipment = await self._shipment_repo.update(shipment)
                self._uow.register_aggregate(shipment)

            await self._uow.commit()

        if new_count > 0:
            self._logger.info(
                "Tracking updated",
                shipment_id=str(shipment.id),
                new_events=new_count,
            )
        return IngestTrackingResult(
            shipment_id=shipment.id,
            new_events_count=new_count,
        )
