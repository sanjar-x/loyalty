"""Inbox store — UNIQUE (event_id, consumer) deduplication."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.order.domain.interfaces import IInboxStore
from src.modules.order.infrastructure.models import OrderInboxEventModel


class InboxStore(IInboxStore):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def try_record(self, *, event_id: uuid.UUID, consumer: str) -> bool:
        row = OrderInboxEventModel(event_id=event_id, consumer=consumer)
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            return False
        return True
