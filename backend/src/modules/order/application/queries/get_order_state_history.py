"""Query: order state history (audit log)."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.order.application.queries.read_models import OrderStateHistoryEntry
from src.modules.order.infrastructure.models import OrderStateHistoryModel


@dataclass(frozen=True)
class GetOrderStateHistoryQuery:
    order_id: uuid.UUID


class GetOrderStateHistoryHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, query: GetOrderStateHistoryQuery
    ) -> list[OrderStateHistoryEntry]:
        stmt = (
            select(OrderStateHistoryModel)
            .where(OrderStateHistoryModel.order_id == query.order_id)
            .order_by(OrderStateHistoryModel.occurred_at.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            OrderStateHistoryEntry(
                id=r.id,
                from_status=r.from_status,
                to_status=r.to_status,
                event_type=r.event_type,
                event_id=r.event_id,
                actor_type=r.actor_type,
                actor_id=r.actor_id,
                metadata=r.event_metadata,
                occurred_at=r.occurred_at,
            )
            for r in rows
        ]
