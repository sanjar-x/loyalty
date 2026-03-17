# src/modules/identity/application/queries/get_my_sessions.py
import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SessionInfo(BaseModel):
    id: uuid.UUID
    ip_address: str | None
    user_agent: str | None
    is_revoked: bool
    created_at: datetime
    expires_at: datetime
    is_current: bool = False


@dataclass(frozen=True)
class GetMySessionsQuery:
    identity_id: uuid.UUID
    current_session_id: uuid.UUID


_MY_SESSIONS_SQL = text(
    "SELECT id, ip_address, user_agent, is_revoked, created_at, expires_at "
    "FROM sessions "
    "WHERE identity_id = :identity_id AND is_revoked = false "
    "ORDER BY created_at DESC"
)


class GetMySessionsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetMySessionsQuery) -> list[SessionInfo]:
        result = await self._session.execute(_MY_SESSIONS_SQL, {"identity_id": query.identity_id})
        return [
            SessionInfo(
                id=row["id"],
                ip_address=str(row["ip_address"]) if row["ip_address"] else None,
                user_agent=row["user_agent"],
                is_revoked=row["is_revoked"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                is_current=(row["id"] == query.current_session_id),
            )
            for row in result.mappings().all()
        ]
