"""Query handler for retrieving the current user's active sessions.

Returns a list of active (non-revoked) sessions for the authenticated
identity, marking which one is the current session.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SessionInfo(BaseModel):
    """Read model for a session summary.

    Attributes:
        id: The session's UUID.
        ip_address: Client IP address at session creation, if available.
        user_agent: Client User-Agent string, if available.
        created_at: Timestamp when the session was created.
        expires_at: Timestamp when the session's refresh token expires.
        is_current: True if this is the requesting session.
    """

    id: uuid.UUID
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False


@dataclass(frozen=True)
class GetMySessionsQuery:
    """Query to retrieve active sessions for the current identity.

    Attributes:
        identity_id: The identity whose sessions to retrieve.
        current_session_id: The session making the request (marked as current).
    """

    identity_id: uuid.UUID
    current_session_id: uuid.UUID


_MY_SESSIONS_SQL = text(
    "SELECT id, ip_address, user_agent, created_at, expires_at "
    "FROM sessions "
    "WHERE identity_id = :identity_id AND is_revoked = false AND expires_at > now() "
    "ORDER BY created_at DESC"
)


class GetMySessionsHandler:
    """Handles the get-my-sessions query using raw SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetMySessionsQuery) -> list[SessionInfo]:
        """Execute the query and return active sessions for the identity.

        Args:
            query: The get-my-sessions query.

        Returns:
            List of active sessions ordered by creation time (newest first).
        """
        result = await self._session.execute(_MY_SESSIONS_SQL, {"identity_id": query.identity_id})
        return [
            SessionInfo(
                id=row["id"],
                ip_address=str(row["ip_address"]) if row["ip_address"] else None,
                user_agent=row["user_agent"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                is_current=(row["id"] == query.current_session_id),
            )
            for row in result.mappings().all()
        ]
