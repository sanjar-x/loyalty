"""Order state history writer — append-only audit log."""

import uuid
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.order.domain.interfaces import (
    HistoryActor,
    IOrderStateHistoryWriter,
)
from src.modules.order.domain.value_objects import OrderStatus
from src.modules.order.infrastructure.models import OrderStateHistoryModel


class OrderStateHistoryWriter(IOrderStateHistoryWriter):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        order_id: uuid.UUID,
        from_status: OrderStatus | None,
        to_status: OrderStatus,
        event_type: str,
        event_id: uuid.UUID,
        actor: HistoryActor,
        metadata: dict | None,
        occurred_at: datetime,
    ) -> None:
        row = OrderStateHistoryModel(
            order_id=order_id,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value,
            event_type=event_type,
            event_id=event_id,
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            event_metadata=metadata,
            occurred_at=occurred_at,
        )
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError:
            # UNIQUE event_id violation = duplicate transition recorded by
            # another worker; safe to ignore.
            await self._session.rollback()
