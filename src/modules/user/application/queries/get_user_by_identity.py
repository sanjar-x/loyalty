# src/modules/user/application/queries/get_user_by_identity.py
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class GetUserByIdentityQuery:
    identity_id: uuid.UUID


_GET_USER_ID_SQL = text("SELECT id FROM users WHERE id = :identity_id")


class GetUserByIdentityHandler:
    """Internal: used by backward-compatible get_current_user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetUserByIdentityQuery) -> uuid.UUID | None:
        """Returns user_id if user exists, None otherwise."""
        result = await self._session.execute(_GET_USER_ID_SQL, {"identity_id": query.identity_id})
        row = result.mappings().first()
        return row["id"] if row else None
