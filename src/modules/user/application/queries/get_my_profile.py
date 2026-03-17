# src/modules/user/application/queries/get_my_profile.py
import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.domain.exceptions import UserNotFoundError


class UserProfile(BaseModel):
    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None


@dataclass(frozen=True)
class GetMyProfileQuery:
    user_id: uuid.UUID


_GET_PROFILE_SQL = text(
    "SELECT id, profile_email, first_name, last_name, phone FROM users WHERE id = :user_id"
)


class GetMyProfileHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetMyProfileQuery) -> UserProfile:
        result = await self._session.execute(_GET_PROFILE_SQL, {"user_id": query.user_id})
        row = result.mappings().first()
        if row is None:
            raise UserNotFoundError(query.user_id)

        return UserProfile(
            id=row["id"],
            profile_email=row["profile_email"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row["phone"],
        )
