"""Provider-account repository — Data Mapper for ``ProviderAccountModel``.

Translates between the ``ProviderAccount`` domain aggregate and the
``provider_accounts`` ORM table. Used by the admin CRUD command and
query handlers; the bootstrap path reads the ORM directly for
performance and to avoid coupling startup to the domain layer.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.logistics.domain.interfaces import IProviderAccountRepository
from src.modules.logistics.domain.provider_account import ProviderAccount
from src.modules.logistics.domain.value_objects import ProviderCode
from src.modules.logistics.infrastructure.models import ProviderAccountModel


class ProviderAccountRepository(IProviderAccountRepository):
    """Async-SQLAlchemy implementation of ``IProviderAccountRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- Public interface ---------------------------------------------------

    async def add(self, account: ProviderAccount) -> ProviderAccount:
        orm = self._to_orm(account)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return self._to_domain(orm)

    async def get_by_id(self, account_id: uuid.UUID) -> ProviderAccount | None:
        orm = await self._session.get(ProviderAccountModel, account_id)
        return self._to_domain(orm) if orm else None

    async def get_active_by_provider_code(
        self, provider_code: ProviderCode
    ) -> ProviderAccount | None:
        # Filtered by ``is_active = true`` so the partial unique index
        # guarantees at most one match — multiple inactive rows for the
        # same code are legitimate (credential-rotation staging).
        stmt = select(ProviderAccountModel).where(
            ProviderAccountModel.provider_code == provider_code,
            ProviderAccountModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_all(self) -> list[ProviderAccount]:
        stmt = select(ProviderAccountModel).order_by(
            ProviderAccountModel.provider_code, ProviderAccountModel.created_at
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def update(self, account: ProviderAccount) -> ProviderAccount:
        orm = await self._session.get(ProviderAccountModel, account.id)
        if orm is None:
            raise ValueError(f"ProviderAccount {account.id} not found")

        orm.provider_code = account.provider_code
        orm.name = account.name
        orm.is_active = account.is_active
        orm.credentials_json = account.credentials
        orm.config_json = account.config
        # ``updated_at`` is set by the ORM ``onupdate=func.now()`` clause —
        # we flush to trigger it, then refresh to read the DB value back.
        await self._session.flush()
        await self._session.refresh(orm)
        return self._to_domain(orm)

    async def delete(self, account_id: uuid.UUID) -> bool:
        stmt = (
            delete(ProviderAccountModel)
            .where(ProviderAccountModel.id == account_id)
            .returning(ProviderAccountModel.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # -- Mapping ------------------------------------------------------------

    @staticmethod
    def _to_orm(account: ProviderAccount) -> ProviderAccountModel:
        return ProviderAccountModel(
            id=account.id,
            provider_code=account.provider_code,
            name=account.name,
            is_active=account.is_active,
            credentials_json=account.credentials,
            config_json=account.config,
        )

    @staticmethod
    def _to_domain(orm: ProviderAccountModel) -> ProviderAccount:
        return ProviderAccount(
            id=orm.id,
            provider_code=orm.provider_code,
            name=orm.name,
            is_active=bool(orm.is_active),
            credentials=dict(orm.credentials_json or {}),
            config=dict(orm.config_json or {}),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
