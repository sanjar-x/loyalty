# src/modules/identity/infrastructure/repositories/session_repository.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.identity.domain.entities import Session
from src.modules.identity.domain.interfaces import ISessionRepository
from src.modules.identity.infrastructure.models import SessionModel, SessionRoleModel


class SessionRepository(ISessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    def _to_domain(self, orm: SessionModel) -> Session:
        role_ids = [sr.role_id for sr in orm.activated_roles]
        return Session(
            id=orm.id,
            identity_id=orm.identity_id,
            refresh_token_hash=orm.refresh_token_hash,
            ip_address=orm.ip_address or "",
            user_agent=orm.user_agent or "",
            is_revoked=orm.is_revoked,
            created_at=orm.created_at,
            expires_at=orm.expires_at,
            activated_roles=role_ids,
        )

    async def add(self, session: Session) -> Session:
        orm = SessionModel(
            id=session.id,
            identity_id=session.identity_id,
            refresh_token_hash=session.refresh_token_hash,
            ip_address=session.ip_address or None,
            user_agent=session.user_agent or None,
            is_revoked=session.is_revoked,
            expires_at=session.expires_at,
        )
        self._session.add(orm)
        await self._session.flush()
        return session

    async def get(self, session_id: uuid.UUID) -> Session | None:
        stmt = (
            select(SessionModel)
            .options(selectinload(SessionModel.activated_roles))
            .where(SessionModel.id == session_id)
        )
        result = await self._session.execute(stmt)
        orm = result.unique().scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_refresh_token_hash(self, token_hash: str) -> Session | None:
        stmt = (
            select(SessionModel)
            .options(selectinload(SessionModel.activated_roles))
            .where(SessionModel.refresh_token_hash == token_hash)
        )
        result = await self._session.execute(stmt)
        orm = result.unique().scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def update(self, session: Session) -> None:
        stmt = (
            update(SessionModel)
            .where(SessionModel.id == session.id)
            .values(
                refresh_token_hash=session.refresh_token_hash,
                is_revoked=session.is_revoked,
            )
        )
        await self._session.execute(stmt)

    async def revoke_all_for_identity(self, identity_id: uuid.UUID) -> list[uuid.UUID]:
        now = datetime.now(UTC)
        stmt = select(SessionModel.id).where(
            SessionModel.identity_id == identity_id,
            SessionModel.is_revoked.is_(False),
            SessionModel.expires_at > now,
        )
        result = await self._session.execute(stmt)
        session_ids = [row[0] for row in result.all()]

        if session_ids:
            update_stmt = (
                update(SessionModel).where(SessionModel.id.in_(session_ids)).values(is_revoked=True)
            )
            await self._session.execute(update_stmt)

        return session_ids

    async def count_active(self, identity_id: uuid.UUID) -> int:
        now = datetime.now(UTC)
        stmt = (
            select(func.count())
            .select_from(SessionModel)
            .where(
                SessionModel.identity_id == identity_id,
                SessionModel.is_revoked.is_(False),
                SessionModel.expires_at > now,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_active_session_ids(self, identity_id: uuid.UUID) -> list[uuid.UUID]:
        now = datetime.now(UTC)
        stmt = select(SessionModel.id).where(
            SessionModel.identity_id == identity_id,
            SessionModel.is_revoked.is_(False),
            SessionModel.expires_at > now,
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def add_session_roles(
        self,
        session_id: uuid.UUID,
        role_ids: list[uuid.UUID],
    ) -> None:
        if not role_ids:
            return
        values = [{"session_id": session_id, "role_id": rid} for rid in role_ids]
        stmt = insert(SessionRoleModel).values(values)
        await self._session.execute(stmt)

    async def remove_session_role(
        self,
        session_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> None:
        stmt = delete(SessionRoleModel).where(
            SessionRoleModel.session_id == session_id,
            SessionRoleModel.role_id == role_id,
        )
        await self._session.execute(stmt)
