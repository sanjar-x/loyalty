# src/modules/user/application/queries/get_user_by_identity.py
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.infrastructure.models import UserModel


@dataclass(frozen=True)
class GetUserByIdentityQuery:
    identity_id: uuid.UUID


class GetUserByIdentityHandler:
    """Internal: used by backward-compatible get_current_user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetUserByIdentityQuery) -> uuid.UUID | None:
        """Returns user_id if user exists, None otherwise."""
        orm = await self._session.get(UserModel, query.identity_id)
        return orm.id if orm else None
