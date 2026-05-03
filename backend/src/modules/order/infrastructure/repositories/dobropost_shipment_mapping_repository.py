"""DobroPost shipment mapping repository.

Resolves either direction of the bijection between DobroPost's
auto-incrementing integer id and the deterministic UUID we expose to
the rest of Order's application layer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.order.application.ports import (
    DobroPostShipmentMappingRecord,
    IDobroPostShipmentMappingRepository,
)
from src.modules.order.infrastructure.models import (
    DobroPostShipmentMappingModel,
)


class DobroPostShipmentMappingRepository(IDobroPostShipmentMappingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        order_id: uuid.UUID,
        shipment_uuid: uuid.UUID,
        dp_shipment_id: int,
        incoming_declaration: str,
        dp_track_number: str | None,
    ) -> None:
        row = DobroPostShipmentMappingModel(
            id=uuid.uuid4(),
            order_id=order_id,
            shipment_uuid=shipment_uuid,
            dp_shipment_id=dp_shipment_id,
            incoming_declaration=incoming_declaration,
            dp_track_number=dp_track_number,
        )
        self._session.add(row)

    async def get_by_shipment_uuid(
        self, shipment_uuid: uuid.UUID
    ) -> DobroPostShipmentMappingRecord | None:
        stmt = select(DobroPostShipmentMappingModel).where(
            DobroPostShipmentMappingModel.shipment_uuid == shipment_uuid
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_record(row) if row else None

    async def get_by_dp_shipment_id(
        self, dp_shipment_id: int
    ) -> DobroPostShipmentMappingRecord | None:
        stmt = select(DobroPostShipmentMappingModel).where(
            DobroPostShipmentMappingModel.dp_shipment_id == dp_shipment_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_record(row) if row else None

    async def get_by_order_id(
        self, order_id: uuid.UUID
    ) -> DobroPostShipmentMappingRecord | None:
        stmt = select(DobroPostShipmentMappingModel).where(
            DobroPostShipmentMappingModel.order_id == order_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_record(row) if row else None

    async def update_status(
        self,
        *,
        dp_shipment_id: int,
        last_status_id: int,
        dp_track_number: str | None = None,
    ) -> None:
        stmt = select(DobroPostShipmentMappingModel).where(
            DobroPostShipmentMappingModel.dp_shipment_id == dp_shipment_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return
        row.last_status_id = last_status_id
        row.last_status_at = datetime.now(UTC)
        if dp_track_number is not None:
            row.dp_track_number = dp_track_number


def _to_record(
    row: DobroPostShipmentMappingModel,
) -> DobroPostShipmentMappingRecord:
    return DobroPostShipmentMappingRecord(
        order_id=row.order_id,
        shipment_uuid=row.shipment_uuid,
        dp_shipment_id=row.dp_shipment_id,
        incoming_declaration=row.incoming_declaration,
        dp_track_number=row.dp_track_number,
        last_status_id=row.last_status_id,
        last_status_at=row.last_status_at,
    )
