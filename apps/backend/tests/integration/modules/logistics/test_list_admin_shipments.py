"""Integration tests for ``ListAdminShipmentsHandler`` (LOG-003).

Spins up real shipments rows via the ORM and exercises every filter
plus the cursor pagination. Each test runs inside the per-test nested
transaction (``db_session`` fixture) so seeded data does not leak
between tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.logistics.application.queries.list_admin_shipments import (
    ListAdminShipmentsHandler,
    ListAdminShipmentsQuery,
)
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    PROVIDER_DOBROPOST,
    PROVIDER_YANDEX_DELIVERY,
    ShipmentStatus,
    TrackingStatus,
)
from src.modules.logistics.infrastructure.models import ShipmentModel

pytestmark = pytest.mark.integration


def _shipment(
    *,
    provider_code: str = PROVIDER_CDEK,
    status: ShipmentStatus = ShipmentStatus.BOOKED,
    order_id: uuid.UUID | None = None,
    tracking_number: str | None = None,
    created_at: datetime | None = None,
    destination_city: str = "Москва",
    latest_tracking_status: TrackingStatus | None = None,
) -> ShipmentModel:
    """Build a minimal valid ShipmentModel for seeding."""
    now = created_at or datetime.now(UTC)
    return ShipmentModel(
        id=uuid.uuid4(),
        order_id=order_id,
        provider_code=provider_code,
        service_code="136",
        delivery_type="pickup_point",
        status=status.value,
        origin_json={"country_code": "RU", "city": "Москва"},
        destination_json={"country_code": "RU", "city": destination_city},
        sender_json={"first_name": "А", "last_name": "Б", "phone": "+79001112233"},
        recipient_json={"first_name": "В", "last_name": "Г", "phone": "+79004445566"},
        parcels_json=[{"weight": {"grams": 1000}, "dimensions": None, "items": []}],
        quoted_cost_amount=50_000,
        quoted_cost_currency="RUB",
        cod_json=None,
        provider_shipment_id=None,
        tracking_number=tracking_number,
        provider_payload="{}",
        latest_tracking_status=latest_tracking_status,
        failure_reason=None,
        estimated_delivery_json=None,
        pending_edit_tasks_json=[],
        scheduled_intake_json=None,
        registered_returns_json=[],
        created_at=now,
        updated_at=now,
        booked_at=now if status is ShipmentStatus.BOOKED else None,
        cancelled_at=None,
        cross_border_arrived_at=None,
        version=1,
    )


async def _seed_shipments(
    db_session: AsyncSession, shipments: list[ShipmentModel]
) -> None:
    for s in shipments:
        db_session.add(s)
    await db_session.flush()


async def test_no_filters_returns_all_ordered_desc(db_session: AsyncSession) -> None:
    base = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    rows = [_shipment(created_at=base + timedelta(hours=i)) for i in range(3)]
    await _seed_shipments(db_session, rows)

    handler = ListAdminShipmentsHandler(db_session)
    page = await handler.handle(ListAdminShipmentsQuery())

    assert len(page.items) == 3
    # Ordered by created_at DESC.
    assert (
        page.items[0].created_at > page.items[1].created_at > page.items[2].created_at
    )
    assert page.next_cursor is None


async def test_empty_result(db_session: AsyncSession) -> None:
    handler = ListAdminShipmentsHandler(db_session)
    page = await handler.handle(ListAdminShipmentsQuery())
    assert page.items == []
    assert page.next_cursor is None


async def test_filter_by_provider(db_session: AsyncSession) -> None:
    await _seed_shipments(
        db_session,
        [
            _shipment(provider_code=PROVIDER_CDEK),
            _shipment(provider_code=PROVIDER_YANDEX_DELIVERY),
            _shipment(provider_code=PROVIDER_DOBROPOST),
        ],
    )

    handler = ListAdminShipmentsHandler(db_session)
    page = await handler.handle(ListAdminShipmentsQuery(provider=PROVIDER_CDEK))

    assert len(page.items) == 1
    assert page.items[0].provider_code == PROVIDER_CDEK


async def test_filter_by_status(db_session: AsyncSession) -> None:
    await _seed_shipments(
        db_session,
        [
            _shipment(status=ShipmentStatus.DRAFT),
            _shipment(status=ShipmentStatus.BOOKED),
            _shipment(status=ShipmentStatus.CANCELLED),
        ],
    )

    handler = ListAdminShipmentsHandler(db_session)
    page = await handler.handle(ListAdminShipmentsQuery(status=ShipmentStatus.BOOKED))

    assert len(page.items) == 1
    assert page.items[0].status == "booked"


async def test_filter_by_order_id(db_session: AsyncSession) -> None:
    target_order_id = uuid.uuid4()
    other_order_id = uuid.uuid4()
    await _seed_shipments(
        db_session,
        [
            _shipment(order_id=target_order_id),
            _shipment(order_id=other_order_id),
            _shipment(order_id=None),
        ],
    )

    handler = ListAdminShipmentsHandler(db_session)
    page = await handler.handle(ListAdminShipmentsQuery(order_id=target_order_id))

    assert len(page.items) == 1
    assert page.items[0].order_id == target_order_id


async def test_filter_by_date_range(db_session: AsyncSession) -> None:
    await _seed_shipments(
        db_session,
        [
            _shipment(created_at=datetime(2026, 4, 1, tzinfo=UTC)),
            _shipment(created_at=datetime(2026, 5, 1, tzinfo=UTC)),
            _shipment(created_at=datetime(2026, 6, 1, tzinfo=UTC)),
        ],
    )

    handler = ListAdminShipmentsHandler(db_session)
    page = await handler.handle(
        ListAdminShipmentsQuery(
            created_after=datetime(2026, 4, 15, tzinfo=UTC),
            created_before=datetime(2026, 5, 15, tzinfo=UTC),
        )
    )

    assert len(page.items) == 1
    assert page.items[0].created_at == datetime(2026, 5, 1, tzinfo=UTC)


async def test_filter_by_tracking_number_substring(db_session: AsyncSession) -> None:
    await _seed_shipments(
        db_session,
        [
            _shipment(tracking_number="CDEK-AB-123456"),
            _shipment(tracking_number="YND-XY-789"),
            _shipment(tracking_number=None),
        ],
    )

    handler = ListAdminShipmentsHandler(db_session)

    # Case-insensitive substring match.
    page = await handler.handle(
        ListAdminShipmentsQuery(tracking_number_contains="ab-12")
    )
    assert len(page.items) == 1
    assert page.items[0].tracking_number == "CDEK-AB-123456"

    # Empty / whitespace-only filter is ignored.
    page = await handler.handle(ListAdminShipmentsQuery(tracking_number_contains="   "))
    assert len(page.items) == 3


async def test_tracking_number_filter_escapes_wildcards(
    db_session: AsyncSession,
) -> None:
    await _seed_shipments(
        db_session,
        [
            _shipment(tracking_number="50%off"),
            _shipment(tracking_number="ABC123"),
        ],
    )

    handler = ListAdminShipmentsHandler(db_session)
    page = await handler.handle(ListAdminShipmentsQuery(tracking_number_contains="50%"))
    # Without escape, ``%`` would match anything; we want literal-only match.
    assert len(page.items) == 1
    assert page.items[0].tracking_number == "50%off"


async def test_combined_filters(db_session: AsyncSession) -> None:
    target = _shipment(
        provider_code=PROVIDER_CDEK,
        status=ShipmentStatus.BOOKED,
        created_at=datetime(2026, 5, 5, tzinfo=UTC),
    )
    await _seed_shipments(
        db_session,
        [
            target,
            _shipment(
                provider_code=PROVIDER_YANDEX_DELIVERY,
                status=ShipmentStatus.BOOKED,
                created_at=datetime(2026, 5, 5, tzinfo=UTC),
            ),
            _shipment(
                provider_code=PROVIDER_CDEK,
                status=ShipmentStatus.DRAFT,
                created_at=datetime(2026, 5, 5, tzinfo=UTC),
            ),
            _shipment(
                provider_code=PROVIDER_CDEK,
                status=ShipmentStatus.BOOKED,
                created_at=datetime(2026, 4, 1, tzinfo=UTC),
            ),
        ],
    )

    handler = ListAdminShipmentsHandler(db_session)
    page = await handler.handle(
        ListAdminShipmentsQuery(
            provider=PROVIDER_CDEK,
            status=ShipmentStatus.BOOKED,
            created_after=datetime(2026, 5, 1, tzinfo=UTC),
            created_before=datetime(2026, 6, 1, tzinfo=UTC),
        )
    )

    assert len(page.items) == 1
    assert page.items[0].id == target.id


async def test_cursor_pagination_forward(db_session: AsyncSession) -> None:
    base = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    rows = [_shipment(created_at=base + timedelta(hours=i)) for i in range(5)]
    await _seed_shipments(db_session, rows)

    handler = ListAdminShipmentsHandler(db_session)

    page1 = await handler.handle(ListAdminShipmentsQuery(limit=2))
    assert len(page1.items) == 2
    assert page1.next_cursor is not None

    page2 = await handler.handle(
        ListAdminShipmentsQuery(limit=2, cursor=page1.next_cursor)
    )
    assert len(page2.items) == 2
    assert page2.next_cursor is not None
    # No overlap between pages.
    assert {row.id for row in page2.items}.isdisjoint({row.id for row in page1.items})

    page3 = await handler.handle(
        ListAdminShipmentsQuery(limit=2, cursor=page2.next_cursor)
    )
    assert len(page3.items) == 1
    assert page3.next_cursor is None


async def test_limit_is_clamped(db_session: AsyncSession) -> None:
    base = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    await _seed_shipments(
        db_session,
        [_shipment(created_at=base + timedelta(hours=i)) for i in range(3)],
    )

    handler = ListAdminShipmentsHandler(db_session)

    # ``limit=0`` is not allowed in the API layer (Query ge=1) but the
    # handler must clamp defensively in case it's invoked directly.
    page = await handler.handle(ListAdminShipmentsQuery(limit=0))
    assert len(page.items) >= 1

    page_huge = await handler.handle(ListAdminShipmentsQuery(limit=1_000))
    # Capped at 200, but with only 3 rows we just check we got them all.
    assert len(page_huge.items) == 3


async def test_destination_city_extracted(db_session: AsyncSession) -> None:
    await _seed_shipments(
        db_session,
        [
            _shipment(destination_city="Санкт-Петербург"),
            _shipment(destination_city="Казань"),
        ],
    )

    handler = ListAdminShipmentsHandler(db_session)
    page = await handler.handle(ListAdminShipmentsQuery())

    cities = {item.destination_city for item in page.items}
    assert cities == {"Санкт-Петербург", "Казань"}


async def test_latest_tracking_status_serialised(db_session: AsyncSession) -> None:
    await _seed_shipments(
        db_session,
        [_shipment(latest_tracking_status=TrackingStatus.IN_TRANSIT)],
    )

    handler = ListAdminShipmentsHandler(db_session)
    page = await handler.handle(ListAdminShipmentsQuery())
    assert page.items[0].latest_tracking_status == "in_transit"
