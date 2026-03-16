# src/modules/user/infrastructure/repositories/user_repository.py
import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.domain.entities import User
from src.modules.user.domain.interfaces import IUserRepository
from src.modules.user.infrastructure.models import UserModel


class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: UserModel) -> User:
        return User(
            id=orm.id,
            profile_email=orm.profile_email,
            first_name=orm.first_name,
            last_name=orm.last_name,
            phone=orm.phone,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def add(self, user: User) -> User:
        orm = UserModel(
            id=user.id,
            profile_email=user.profile_email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, user_id: uuid.UUID) -> User | None:
        orm = await self._session.get(UserModel, user_id)
        return self._to_domain(orm) if orm else None

    async def update(self, user: User) -> None:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                profile_email=user.profile_email,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=user.phone,
            )
        )
        await self._session.execute(stmt)
