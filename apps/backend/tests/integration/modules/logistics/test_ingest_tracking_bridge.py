"""Integration tests for the russian-carrier → Order bridge (LOG-002).

Covers the chain on a real PostgreSQL session:

1. ``IngestTrackingHandler`` writes new ``TrackingEvent`` to the Shipment.
2. ``UoW.enqueue_external_event`` stages a ``RussianCarrierTrackingEvent``
   row with a deterministic UUID5 id + ``shipment``/``order`` payload.
3. ``UoW.commit()`` flushes both the Shipment update AND the outbox row
   in the same DB transaction.
4. Replaying the same payload (same status + timestamp) writes nothing
   new — the in-aggregate dedup catches the second event before
   enqueue, and the UUID5 keeps the outbox honest.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.outbox import OutboxMessage
from src.infrastructure.database.uow import UnitOfWork
from src.modules.logistics.application.commands.ingest_tracking import (
    IngestTrackingCommand,
    IngestTrackingHandler,
)
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    ShipmentStatus,
    TrackingEvent,
    TrackingStatus,
)
from src.modules.logistics.infrastructure.models import ShipmentModel
from src.modules.logistics.infrastructure.repositories.shipment import (
    ShipmentRepository,
)

pytestmark = pytest.mark.integration


class _NullLogger:
    """Minimal ILogger stub — these tests don't assert on log output."""

    def bind(self, **_: Any) -> _NullLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def critical(self, *_: Any, **__: Any) -> None: ...
    def debug(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


def _shipment_orm(
    *,
    order_id: uuid.UUID | None,
    provider_shipment_id: str,
) -> ShipmentModel:
    """Build a minimal BOOKED ShipmentModel directly via the ORM mapper."""
    return ShipmentModel(
        id=uuid.uuid4(),
        order_id=order_id,
        provider_code=PROVIDER_CDEK,
        service_code="136",
        delivery_type="pickup_point",
        status=ShipmentStatus.BOOKED.value,
        origin_json={
            "country_code": "RU",
            "city": "Москва",
            "postal_code": "101000",
            "street": "Тверская",
            "house": "1",
        },
        destination_json={
            "country_code": "RU",
            "city": "Москва",
            "postal_code": "101000",
            "street": "Тверская",
            "house": "1",
        },
        sender_json={
            "first_name": "Иван",
            "last_name": "Иванов",
            "phone": "+79001234567",
        },
        recipient_json={
            "first_name": "Иван",
            "last_name": "Иванов",
            "phone": "+79001234567",
        },
        parcels_json=[
            {
                "weight": {"grams": 1000},
                "dimensions": None,
                "declared_value": None,
                "items": [],
            }
        ],
        quoted_cost_amount=50000,
        quoted_cost_currency="RUB",
        cod_json=None,
        provider_shipment_id=provider_shipment_id,
        tracking_number=None,
        provider_payload="{}",
        latest_tracking_status=None,
        failure_reason=None,
        estimated_delivery_json=None,
        pending_edit_tasks_json=[],
        scheduled_intake_json=None,
        registered_returns_json=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        booked_at=datetime.now(UTC),
        cancelled_at=None,
        cross_border_arrived_at=None,
        version=1,
    )


def _track_event(status: TrackingStatus, ts: datetime) -> TrackingEvent:
    return TrackingEvent(
        status=status,
        provider_status_code="3",
        provider_status_name=status.value,
        timestamp=ts,
        location="Moscow",
        description=None,
    )


async def _seed_shipment(
    db_session: AsyncSession, *, order_id: uuid.UUID | None
) -> tuple[uuid.UUID, str]:
    """Insert a fresh ShipmentModel and return its (id, provider_shipment_id).

    Returns plain values — not the ORM instance — so subsequent test code
    doesn't risk lazy-loading a relationship after the session moved on.
    """
    provider_shipment_id = f"CDEK-{uuid.uuid4().hex[:8]}"
    orm = _shipment_orm(
        order_id=order_id,
        provider_shipment_id=provider_shipment_id,
    )
    db_session.add(orm)
    await db_session.flush()
    return orm.id, provider_shipment_id


async def test_in_transit_event_writes_outbox_row(db_session: AsyncSession) -> None:
    order_id = uuid.uuid4()
    shipment_id, provider_shipment_id = await _seed_shipment(
        db_session, order_id=order_id
    )

    repo = ShipmentRepository(db_session)
    uow = UnitOfWork(db_session)
    handler = IngestTrackingHandler(
        shipment_repo=repo,
        uow=uow,
        logger=_NullLogger(),
    )

    ts = datetime(2026, 5, 5, 10, tzinfo=UTC)
    await handler.handle(
        IngestTrackingCommand(
            provider_code=PROVIDER_CDEK,
            provider_shipment_id=provider_shipment_id,
            events=[_track_event(TrackingStatus.IN_TRANSIT, ts)],
        )
    )

    rows = (
        (
            await db_session.execute(
                select(OutboxMessage).where(
                    OutboxMessage.aggregate_id == str(shipment_id),
                    OutboxMessage.event_type == "RussianCarrierTrackingEvent",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    payload = rows[0].payload
    assert payload["order_id"] == str(order_id)
    assert payload["shipment_id"] == str(shipment_id)
    assert payload["canonical_status"] == "IN_TRANSIT"
    assert payload["provider_code"] == PROVIDER_CDEK
    assert payload["tracking_status"] == TrackingStatus.IN_TRANSIT.value


async def test_replaying_same_event_collapses_to_one_outbox_row(
    db_session: AsyncSession,
) -> None:
    """Two ingests of the same (shipment, status, timestamp) tuple produce
    exactly one outbox row. The Shipment aggregate dedup catches the
    second event before enqueue."""
    order_id = uuid.uuid4()
    shipment_id, provider_shipment_id = await _seed_shipment(
        db_session, order_id=order_id
    )

    repo = ShipmentRepository(db_session)
    ts = datetime(2026, 5, 5, 10, tzinfo=UTC)
    cmd = IngestTrackingCommand(
        provider_code=PROVIDER_CDEK,
        provider_shipment_id=provider_shipment_id,
        events=[_track_event(TrackingStatus.READY_FOR_PICKUP, ts)],
    )

    handler = IngestTrackingHandler(
        shipment_repo=repo,
        uow=UnitOfWork(db_session),
        logger=_NullLogger(),
    )
    await handler.handle(cmd)

    handler2 = IngestTrackingHandler(
        shipment_repo=repo,
        uow=UnitOfWork(db_session),
        logger=_NullLogger(),
    )
    await handler2.handle(cmd)

    rows = (
        (
            await db_session.execute(
                select(OutboxMessage).where(
                    OutboxMessage.aggregate_id == str(shipment_id),
                    OutboxMessage.event_type == "RussianCarrierTrackingEvent",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


async def test_does_not_bridge_shipment_without_order_id(
    db_session: AsyncSession,
) -> None:
    """Out-of-band shipments (no Order link) don't pollute the outbox."""
    shipment_id, provider_shipment_id = await _seed_shipment(db_session, order_id=None)

    repo = ShipmentRepository(db_session)
    handler = IngestTrackingHandler(
        shipment_repo=repo,
        uow=UnitOfWork(db_session),
        logger=_NullLogger(),
    )

    await handler.handle(
        IngestTrackingCommand(
            provider_code=PROVIDER_CDEK,
            provider_shipment_id=provider_shipment_id,
            events=[_track_event(TrackingStatus.DELIVERED, datetime.now(UTC))],
        )
    )

    rows = (
        (
            await db_session.execute(
                select(OutboxMessage).where(
                    OutboxMessage.aggregate_id == str(shipment_id),
                    OutboxMessage.event_type == "RussianCarrierTrackingEvent",
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows == []


async def test_bridges_each_added_status_in_one_call(
    db_session: AsyncSession,
) -> None:
    """Multiple ADDED events in one ingest produce multiple outbox rows.
    ACCEPTED has no Order action and should NOT contribute a row."""
    order_id = uuid.uuid4()
    shipment_id, provider_shipment_id = await _seed_shipment(
        db_session, order_id=order_id
    )

    repo = ShipmentRepository(db_session)
    handler = IngestTrackingHandler(
        shipment_repo=repo,
        uow=UnitOfWork(db_session),
        logger=_NullLogger(),
    )
    await handler.handle(
        IngestTrackingCommand(
            provider_code=PROVIDER_CDEK,
            provider_shipment_id=provider_shipment_id,
            events=[
                _track_event(
                    TrackingStatus.IN_TRANSIT,
                    datetime(2026, 5, 1, tzinfo=UTC),
                ),
                _track_event(
                    TrackingStatus.READY_FOR_PICKUP,
                    datetime(2026, 5, 2, tzinfo=UTC),
                ),
                _track_event(
                    TrackingStatus.ACCEPTED,
                    datetime(2026, 5, 3, tzinfo=UTC),
                ),
            ],
        )
    )

    rows = (
        (
            await db_session.execute(
                select(OutboxMessage).where(
                    OutboxMessage.aggregate_id == str(shipment_id),
                    OutboxMessage.event_type == "RussianCarrierTrackingEvent",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2
    statuses = sorted(r.payload["canonical_status"] for r in rows)
    assert statuses == ["AT_PICKUP_POINT", "IN_TRANSIT"]
