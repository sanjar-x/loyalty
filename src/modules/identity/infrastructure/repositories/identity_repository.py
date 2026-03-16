# src/modules/identity/infrastructure/repositories/identity_repository.py
import uuid

from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.modules.identity.domain.entities import Identity, LocalCredentials
from src.modules.identity.domain.interfaces import IIdentityRepository
from src.modules.identity.domain.value_objects import IdentityType
from src.modules.identity.infrastructure.models import (
    IdentityModel,
    LocalCredentialsModel,
)


class IdentityRepository(IIdentityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _identity_to_domain(self, orm: IdentityModel) -> Identity:
        return Identity(
            id=orm.id,
            type=IdentityType(orm.type),
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _credentials_to_domain(self, orm: LocalCredentialsModel) -> LocalCredentials:
        return LocalCredentials(
            identity_id=orm.identity_id,
            email=orm.email,
            password_hash=orm.password_hash,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def add(self, identity: Identity) -> Identity:
        orm = IdentityModel(
            id=identity.id,
            type=identity.type.value,
            is_active=identity.is_active,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._identity_to_domain(orm)

    async def get(self, identity_id: uuid.UUID) -> Identity | None:
        orm = await self._session.get(IdentityModel, identity_id)
        return self._identity_to_domain(orm) if orm else None

    async def get_by_email(
        self,
        email: str,
    ) -> tuple[Identity, LocalCredentials] | None:
        stmt = (
            select(IdentityModel)
            .join(LocalCredentialsModel)
            .options(joinedload(IdentityModel.credentials))
            .where(LocalCredentialsModel.email == email)
        )
        result = await self._session.execute(stmt)
        orm = result.unique().scalar_one_or_none()
        if orm is None or orm.credentials is None:
            return None
        return (
            self._identity_to_domain(orm),
            self._credentials_to_domain(orm.credentials),
        )

    async def add_credentials(self, credentials: LocalCredentials) -> LocalCredentials:
        orm = LocalCredentialsModel(
            identity_id=credentials.identity_id,
            email=credentials.email,
            password_hash=credentials.password_hash,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._credentials_to_domain(orm)

    async def update_credentials(self, credentials: LocalCredentials) -> None:
        stmt = (
            update(LocalCredentialsModel)
            .where(LocalCredentialsModel.identity_id == credentials.identity_id)
            .values(password_hash=credentials.password_hash)
        )
        await self._session.execute(stmt)

    async def email_exists(self, email: str) -> bool:
        stmt = select(exists().where(LocalCredentialsModel.email == email))
        result = await self._session.execute(stmt)
        return result.scalar() or False
