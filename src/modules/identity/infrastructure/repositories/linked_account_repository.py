# src/modules/identity/infrastructure/repositories/linked_account_repository.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import LinkedAccount
from src.modules.identity.domain.interfaces import ILinkedAccountRepository
from src.modules.identity.infrastructure.models import LinkedAccountModel


class LinkedAccountRepository(ILinkedAccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: LinkedAccountModel) -> LinkedAccount:
        return LinkedAccount(
            id=orm.id,
            identity_id=orm.identity_id,
            provider=orm.provider,
            provider_sub_id=orm.provider_sub_id,
            provider_email=orm.provider_email,
        )

    async def add(self, account: LinkedAccount) -> LinkedAccount:
        orm = LinkedAccountModel(
            id=account.id,
            identity_id=account.identity_id,
            provider=account.provider,
            provider_sub_id=account.provider_sub_id,
            provider_email=account.provider_email,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get_by_provider(
        self,
        provider: str,
        provider_sub_id: str,
    ) -> LinkedAccount | None:
        stmt = select(LinkedAccountModel).where(
            LinkedAccountModel.provider == provider,
            LinkedAccountModel.provider_sub_id == provider_sub_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_all_for_identity(
        self,
        identity_id: uuid.UUID,
    ) -> list[LinkedAccount]:
        stmt = select(LinkedAccountModel).where(
            LinkedAccountModel.identity_id == identity_id
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]
