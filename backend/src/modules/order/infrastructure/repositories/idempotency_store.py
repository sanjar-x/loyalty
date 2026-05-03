"""Persistent idempotency key store backed by ``order_idempotency_keys``."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.order.domain.interfaces import IIdempotencyKeyStore
from src.modules.order.infrastructure.models import OrderIdempotencyKeyModel


class IdempotencyKeyStore(IIdempotencyKeyStore):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def reserve(
        self,
        *,
        key: str,
        identity_id: uuid.UUID,
        scope: str,
        expires_at: datetime,
    ) -> bool:
        row = OrderIdempotencyKeyModel(
            key=key,
            scope=scope,
            identity_id=identity_id,
            expires_at=expires_at,
        )
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            return False
        return True

    async def attach_result(
        self, *, key: str, scope: str, resource_id: uuid.UUID
    ) -> None:
        stmt = (
            select(OrderIdempotencyKeyModel)
            .where(OrderIdempotencyKeyModel.key == key)
            .where(OrderIdempotencyKeyModel.scope == scope)
            .with_for_update()
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return
        row.resource_id = resource_id
        await self._session.flush()

    async def get_result(self, *, key: str, scope: str) -> uuid.UUID | None:
        stmt = (
            select(OrderIdempotencyKeyModel.resource_id)
            .where(OrderIdempotencyKeyModel.key == key)
            .where(OrderIdempotencyKeyModel.scope == scope)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
