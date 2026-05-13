"""Ingest a DobroPost webhook into the Outbox via the UoW (ORD-001).

Replaces the prior in-router ``session.add(OutboxMessage(...))`` flow
with a proper application command. The command knows nothing about the
HTTP framing or the auth check (those stay in the router); it just
takes the *normalized* event metadata and atomically routes it through
the UoW so the outbox-relay → consumer → inbox-dedup pipeline observes
external (third-party) facts via the same path as native domain
events.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

# Logical aggregate label routed through the outbox dispatch registry.
_AGGREGATE_TYPE = "DobroPostShipment"

# UUID5 namespace for deterministic ``event_id`` derivation. A retried
# DobroPost POST with the *same* canonical payload yields the same
# ``event_id`` so the consumer-side ``order_inbox_events`` deduper
# collapses retries even if DobroPost itself does not echo an id back.
_DOBROPOST_NS = uuid.UUID("8b6a3f50-e9b2-4d28-a26a-26b16f5dee20")


@dataclass(frozen=True)
class IngestDobroPostWebhookCommand:
    """Inputs for the webhook-ingest command.

    Attributes:
        event_type: PascalCase event name matching the consumer registry
            entry (``DobroPostStatusUpdatedEvent`` /
            ``DobroPostPassportInvalidEvent``).
        dp_shipment_id: DobroPost integer shipment id, ``None`` when the
            payload is malformed (recorded as ``"unknown"`` aggregate id).
        payload: Already-normalized event payload — handler does NOT
            touch wire-shape parsing; the router resolves status names,
            extracts dp_track, etc. before calling.
        canonical_seed: Stable JSON-string snapshot used to derive
            ``event_id`` via UUID5. Built by the router from the
            event_type + aggregate_id + payload tuple so retries with
            identical content produce identical ids.
        correlation_id: Request-correlation marker forwarded from the
            inbound HTTP request.
    """

    event_type: str
    dp_shipment_id: int | None
    payload: dict[str, Any]
    canonical_seed: str
    correlation_id: str | None


class IngestDobroPostWebhookHandler:
    """Wraps the webhook-ingest in a proper UoW transaction.

    Goes through :meth:`IUnitOfWork.enqueue_external_event` so:

    * The outbox row lands in the same DB transaction as any future
      domain mutations the handler might layer in.
    * The UoW's ``IntegrityError`` → ``ConflictError`` /
      ``UnprocessableEntityError`` translation applies — operators see
      the standard error envelope instead of a raw 500.
    * Architecture rule 3 holds: presentation no longer talks to
      infrastructure ORM directly.
    """

    def __init__(self, uow: IUnitOfWork, logger: ILogger) -> None:
        self._uow = uow
        self._logger = logger.bind(handler="IngestDobroPostWebhookHandler")

    async def handle(self, command: IngestDobroPostWebhookCommand) -> None:
        aggregate_id = (
            str(command.dp_shipment_id)
            if command.dp_shipment_id is not None
            else "unknown"
        )
        event_id = uuid.uuid5(_DOBROPOST_NS, command.canonical_seed)
        # Router-level normalised payload + the stable event_id together
        # let the consumer-side inbox dedup retries.
        enriched = {**command.payload, "event_id": str(event_id)}

        async with self._uow:
            self._uow.enqueue_external_event(
                aggregate_type=_AGGREGATE_TYPE,
                aggregate_id=aggregate_id,
                event_type=command.event_type,
                payload=enriched,
                event_id=event_id,
                correlation_id=command.correlation_id,
            )
            await self._uow.commit()

        self._logger.info(
            "dobropost_webhook_ingested",
            event_type=command.event_type,
            dp_shipment_id=command.dp_shipment_id,
            event_id=str(event_id),
        )
