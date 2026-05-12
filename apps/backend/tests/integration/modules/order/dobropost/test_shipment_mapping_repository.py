"""Integration tests for ``DobroPostShipmentMappingRepository``."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.order.infrastructure.repositories.dobropost_shipment_mapping_repository import (
    DobroPostShipmentMappingRepository,
)

pytestmark = pytest.mark.integration


async def _seed_order(session: AsyncSession, order_id: uuid.UUID) -> None:
    """Insert a minimal Order row so the FK on the mapping table holds."""
    await session.execute(
        text(
            """
            INSERT INTO orders (
                id, identity_id, cart_id, status, total_amount, currency,
                pickup_carrier, pickup_point_id,
                recipient_id, recipient_full_name_ru, recipient_full_name_lat,
                recipient_phone, recipient_email,
                recipient_passport_serial, recipient_passport_number,
                recipient_passport_issue_date, recipient_birth_date,
                recipient_inn,
                version, created_at, updated_at
            ) VALUES (
                :id, :ident, :cart, 'pending', 1000, 'RUB',
                'cdek', 'pp-1',
                :recipient, 'Иван Иванов', 'Ivan Ivanov',
                '+79108897762', 'a@b.ru',
                '1234', '567890',
                DATE '2015-05-22', DATE '1990-01-01',
                '500100732272',
                0, NOW(), NOW()
            )
            """
        ),
        {
            "id": order_id,
            "ident": uuid.uuid4(),
            "cart": uuid.uuid4(),
            "recipient": uuid.uuid4(),
        },
    )


async def test_add_and_lookup_by_three_keys(db_session: AsyncSession) -> None:
    repo = DobroPostShipmentMappingRepository(db_session)
    order_id = uuid.uuid4()
    shipment_uuid = uuid.uuid4()
    await _seed_order(db_session, order_id)
    await repo.add(
        order_id=order_id,
        shipment_uuid=shipment_uuid,
        dp_shipment_id=12345,
        incoming_declaration="LP00012345CN",
        dp_track_number="DP12345",
    )
    await db_session.flush()

    by_uuid = await repo.get_by_shipment_uuid(shipment_uuid)
    by_int = await repo.get_by_dp_shipment_id(12345)
    by_order = await repo.get_by_order_id(order_id)

    assert by_uuid is not None
    assert by_uuid.dp_shipment_id == 12345
    assert by_int is not None
    assert by_int.shipment_uuid == shipment_uuid
    assert by_order is not None
    assert by_order.dp_track_number == "DP12345"


async def test_update_status_persists_status_id_and_track(
    db_session: AsyncSession,
) -> None:
    repo = DobroPostShipmentMappingRepository(db_session)
    order_id = uuid.uuid4()
    await _seed_order(db_session, order_id)
    await repo.add(
        order_id=order_id,
        shipment_uuid=uuid.uuid4(),
        dp_shipment_id=99,
        incoming_declaration="LP99",
        dp_track_number=None,
    )
    await db_session.flush()

    await repo.update_status(
        dp_shipment_id=99, last_status_id=649, dp_track_number="DPNEW"
    )
    await db_session.flush()
    fresh = await repo.get_by_dp_shipment_id(99)
    assert fresh is not None
    assert fresh.last_status_id == 649
    assert fresh.dp_track_number == "DPNEW"
    assert fresh.last_status_at is not None


async def test_get_by_unknown_keys_returns_none(
    db_session: AsyncSession,
) -> None:
    repo = DobroPostShipmentMappingRepository(db_session)
    assert await repo.get_by_dp_shipment_id(424242) is None
    assert await repo.get_by_shipment_uuid(uuid.uuid4()) is None
    assert await repo.get_by_order_id(uuid.uuid4()) is None
