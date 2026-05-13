"""Concrete adapters for :class:`IIdempotencyStore` / :class:`IInboxStore`.

Both adapters rely on a single ``UNIQUE`` index for atomicity:
``INSERT`` is racy, but the database serializes the conflict and the
adapter translates an ``IntegrityError`` into a ``False`` return. No
explicit application-level locking required.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.idempotency.models import (
    ConsumerInboxModel,
    IdempotencyKeyModel,
)
from src.shared.interfaces.idempotency import IIdempotencyStore, IInboxStore


class SqlIdempotencyStore(IIdempotencyStore):
    """PostgreSQL-backed idempotency-key store."""

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
        row = IdempotencyKeyModel(
            scope=scope,
            key=key,
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
            select(IdempotencyKeyModel)
            .where(IdempotencyKeyModel.scope == scope)
            .where(IdempotencyKeyModel.key == key)
            .with_for_update()
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return
        row.resource_id = resource_id
        await self._session.flush()

    async def get_result(self, *, key: str, scope: str) -> uuid.UUID | None:
        stmt = (
            select(IdempotencyKeyModel.resource_id)
            .where(IdempotencyKeyModel.scope == scope)
            .where(IdempotencyKeyModel.key == key)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()


class SqlInboxStore(IInboxStore):
    """PostgreSQL-backed consumer-inbox store."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def try_record(self, *, event_id: uuid.UUID, consumer: str) -> bool:
        row = ConsumerInboxModel(event_id=event_id, consumer=consumer)
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            return False
        return True
