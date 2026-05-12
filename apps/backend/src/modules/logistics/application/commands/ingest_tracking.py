"""
Command handler: ingest tracking updates (from webhook or polling).

Unified ingestion path — both webhook adapters and polling tasks
call this handler. Deduplication is handled by the Shipment aggregate.
"""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime

from src.modules.logistics.application.dto import IngestTrackingResult
from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import IShipmentRepository
from src.modules.logistics.domain.russian_carrier_status_map import (
    russian_carrier_status_map,
)
from src.modules.logistics.domain.value_objects import (
    ProviderCode,
    TrackingAppendOutcome,
    TrackingEvent,
)
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork

# UUID5 namespace for ``RussianCarrierTrackingEvent`` external-event ids.
# Stable across processes so identical (shipment, status, occurred_at)
# tuples produce the same outbox row id, collapsing duplicate
# webhook deliveries before they reach the consumer-side inbox dedup.
_RUSSIAN_CARRIER_NS = uuid.UUID("5b3a3f8c-7c2a-4d4d-9d2c-3f1d2e2a4b1c")


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


__all__ = ["IngestTrackingCommand", "IngestTrackingHandler", "IngestTrackingResult"]


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
                        "provider_code": command.provider_code,
                        "provider_shipment_id": command.provider_shipment_id,
                    }
                )

            added = 0
            replaced = 0
            added_events: list[TrackingEvent] = []
            for event in command.events:
                outcome = shipment.append_tracking_event(event)
                if outcome is TrackingAppendOutcome.ADDED:
                    added += 1
                    added_events.append(event)
                elif outcome is TrackingAppendOutcome.REPLACED:
                    replaced += 1

            # LOG-002 (fixes B1 audit GAP A) — bridge russian-carrier
            # tracking statuses into the Order FSM via the outbox.
            # Only newly ADDED events qualify (REPLACED is a richer-
            # info upgrade of an already-bridged event; rebroadcasting
            # would route the same FSM action twice). DobroPost is
            # filtered inside ``russian_carrier_status_map`` —
            # cross-border arrival is owned by
            # ``DobroPostStatusUpdatedConsumer``.
            if added_events and shipment.order_id is not None:
                self._enqueue_russian_carrier_actions(shipment, added_events)

            # Commit on either ADDED or REPLACED so a richer-info
            # upgrade for an existing duplicate (better location /
            # description text from a webhook arriving after the
            # poll already booked the bare event) is persisted.
            if added or replaced:
                shipment = await self._shipment_repo.update(shipment)
                self._uow.register_aggregate(shipment)
                await self._uow.commit()

        if added or replaced:
            self._logger.info(
                "Tracking updated",
                shipment_id=str(shipment.id),
                new_events=added,
                replaced_events=replaced,
            )
        return IngestTrackingResult(
            shipment_id=shipment.id,
            new_events_count=added,
        )

    def _enqueue_russian_carrier_actions(
        self,
        shipment: Shipment,
        new_events: list[TrackingEvent],
    ) -> None:
        """Stage one ``RussianCarrierTrackingEvent`` per FSM-relevant event.

        Skips events whose status doesn't map to an Order action (status
        map returns ``None``). Idempotency rides on the UUID5 event id
        derived from (shipment_id, status, occurred_at) — the
        consumer-side inbox dedup is the second line of defence.
        """
        order_id = shipment.order_id
        assert order_id is not None  # narrowed by caller

        for event in new_events:
            action = russian_carrier_status_map(event.status, shipment.provider_code)
            if action is None:
                continue
            event_id = _build_event_id(
                shipment_id=shipment.id,
                status=event.status.value,
                occurred_at=event.timestamp,
            )
            self._uow.enqueue_external_event(
                aggregate_type="shipment",
                aggregate_id=str(shipment.id),
                event_type="RussianCarrierTrackingEvent",
                event_id=event_id,
                payload={
                    "order_id": str(order_id),
                    "shipment_id": str(shipment.id),
                    "provider_code": shipment.provider_code,
                    "canonical_status": action.value,
                    "tracking_status": event.status.value,
                    "occurred_at": event.timestamp.isoformat(),
                },
            )
            self._logger.info(
                "russian_carrier.bridge.enqueued",
                shipment_id=str(shipment.id),
                order_id=str(order_id),
                provider_code=shipment.provider_code,
                tracking_status=event.status.value,
                action=action.value,
            )


def _build_event_id(
    *, shipment_id: uuid.UUID, status: str, occurred_at: datetime
) -> uuid.UUID:
    """Derive a deterministic UUID5 from the three fields that identify the
    event. Microsecond-precision timestamp keeps the id stable across
    re-deliveries while still distinguishing genuinely different events
    that share status + shipment.
    """
    seed = f"{shipment_id}|{status}|{occurred_at.isoformat()}"
    digest = hashlib.sha256(seed.encode("utf-8")).digest()[:16]
    return uuid.UUID(bytes=digest, version=5)
