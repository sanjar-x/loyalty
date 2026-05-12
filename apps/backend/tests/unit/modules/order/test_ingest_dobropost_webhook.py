"""Unit tests for :class:`IngestDobroPostWebhookHandler` (ORD-001).

Locks in the contract that webhook ingest now goes through the UoW's
``enqueue_external_event`` channel — same Outbox/relay pipeline as
native domain events, atomicity preserved.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
import structlog

from src.infrastructure.logging.adapter import StructlogAdapter
from src.modules.order.application.commands.ingest_dobropost_webhook import (
    IngestDobroPostWebhookCommand,
    IngestDobroPostWebhookHandler,
)
from shared.interfaces.entities import AggregateRoot
from shared.interfaces.uow import IUnitOfWork


class _FakeUow(IUnitOfWork):
    """Captures every call so the test can assert what landed."""

    def __init__(self) -> None:
        self.entered: int = 0
        self.committed: int = 0
        self.external_events: list[dict[str, Any]] = []

    async def __aenter__(self) -> IUnitOfWork:
        self.entered += 1
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        return None

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.committed += 1

    async def rollback(self) -> None:
        return None

    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        return None

    def enqueue_external_event(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict,
        event_id=None,
        correlation_id: str | None = None,
    ) -> None:
        self.external_events.append(
            {
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "event_type": event_type,
                "payload": payload,
                "event_id": event_id,
                "correlation_id": correlation_id,
            }
        )


def _logger() -> StructlogAdapter:
    return StructlogAdapter(structlog.get_logger("test"))


def _seed(event_type: str, agg_id: str, payload: dict) -> str:
    return json.dumps(
        {"event_type": event_type, "agg": agg_id, "payload": payload},
        sort_keys=True,
        default=str,
    )


@pytest.mark.asyncio
async def test_handler_routes_through_uow_external_event_channel() -> None:
    uow = _FakeUow()
    handler = IngestDobroPostWebhookHandler(uow=uow, logger=_logger())

    payload = {"dp_shipment_id": 9001, "status_id": 270, "status_label": "Receiving"}
    seed = _seed("DobroPostStatusUpdatedEvent", "9001", payload)

    await handler.handle(
        IngestDobroPostWebhookCommand(
            event_type="DobroPostStatusUpdatedEvent",
            dp_shipment_id=9001,
            payload=payload,
            canonical_seed=seed,
            correlation_id="req-abc",
        )
    )

    assert uow.entered == 1
    assert uow.committed == 1
    assert len(uow.external_events) == 1
    event = uow.external_events[0]
    assert event["aggregate_type"] == "DobroPostShipment"
    assert event["aggregate_id"] == "9001"
    assert event["event_type"] == "DobroPostStatusUpdatedEvent"
    assert event["payload"]["status_id"] == 270
    # Stable event_id derived via UUID5 from the canonical seed.
    assert isinstance(event["event_id"], uuid.UUID)
    # Same payload must produce the same id (consumer-side dedup invariant).
    expected_event_id = uuid.uuid5(
        uuid.UUID("8b6a3f50-e9b2-4d28-a26a-26b16f5dee20"), seed
    )
    assert event["event_id"] == expected_event_id
    # Enriched payload carries the event_id so the consumer-side inbox
    # has a stable dedup key.
    assert event["payload"]["event_id"] == str(expected_event_id)
    assert event["correlation_id"] == "req-abc"


@pytest.mark.asyncio
async def test_handler_uses_unknown_for_missing_dp_shipment_id() -> None:
    uow = _FakeUow()
    handler = IngestDobroPostWebhookHandler(uow=uow, logger=_logger())

    payload = {"dp_shipment_id": None, "status_id": 100}
    seed = _seed("DobroPostStatusUpdatedEvent", "unknown", payload)

    await handler.handle(
        IngestDobroPostWebhookCommand(
            event_type="DobroPostStatusUpdatedEvent",
            dp_shipment_id=None,
            payload=payload,
            canonical_seed=seed,
            correlation_id=None,
        )
    )

    assert uow.external_events[0]["aggregate_id"] == "unknown"


@pytest.mark.asyncio
async def test_identical_seed_produces_identical_event_id() -> None:
    """DobroPost retries with the same payload must collapse into one
    Outbox row by deriving the same UUID5 event_id."""
    uow = _FakeUow()
    handler = IngestDobroPostWebhookHandler(uow=uow, logger=_logger())

    payload = {"dp_shipment_id": 1, "status_id": 220}
    seed = _seed("DobroPostStatusUpdatedEvent", "1", payload)
    cmd = IngestDobroPostWebhookCommand(
        event_type="DobroPostStatusUpdatedEvent",
        dp_shipment_id=1,
        payload=payload,
        canonical_seed=seed,
        correlation_id=None,
    )

    await handler.handle(cmd)
    await handler.handle(cmd)

    # The handler doesn't dedup itself (the consumer does); but both
    # rows must carry the IDENTICAL event_id so the inbox can dedup.
    assert uow.external_events[0]["event_id"] == uow.external_events[1]["event_id"]
