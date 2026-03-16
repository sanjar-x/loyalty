# src/modules/user/application/queries/get_my_profile.py
import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.domain.exceptions import UserNotFoundError
from src.modules.user.infrastructure.models import UserModel


class UserProfile(BaseModel):
    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None


@dataclass(frozen=True)
class GetMyProfileQuery:
    user_id: uuid.UUID


class GetMyProfileHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetMyProfileQuery) -> UserProfile:
        orm = await self._session.get(UserModel, query.user_id)
        if orm is None:
            raise UserNotFoundError(query.user_id)

        return UserProfile(
            id=orm.id,
            profile_email=orm.profile_email,
            first_name=orm.first_name,
            last_name=orm.last_name,
            phone=orm.phone,
        )
