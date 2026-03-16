# src/modules/identity/application/queries/get_my_sessions.py
import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.infrastructure.models import SessionModel


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


class GetMySessionsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetMySessionsQuery) -> list[SessionInfo]:
        stmt = (
            select(SessionModel)
            .where(
                SessionModel.identity_id == query.identity_id,
                SessionModel.is_revoked.is_(False),
            )
            .order_by(SessionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            SessionInfo(
                id=row.id,
                ip_address=row.ip_address,
                user_agent=row.user_agent,
                is_revoked=row.is_revoked,
                created_at=row.created_at,
                expires_at=row.expires_at,
                is_current=(row.id == query.current_session_id),
            )
            for row in rows
        ]
