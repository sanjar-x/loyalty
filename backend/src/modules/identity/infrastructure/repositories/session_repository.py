"""SQLAlchemy implementation of the Session repository.

Maps between SessionModel/SessionRoleModel ORM objects and domain Session
entities using the Data Mapper pattern. Handles session lifecycle including
creation, retrieval, token rotation updates, revocation, and session-role
management.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.identity.domain.entities import Session
from src.modules.identity.domain.interfaces import ISessionRepository
from src.modules.identity.infrastructure.models import SessionModel, SessionRoleModel


class SessionRepository(ISessionRepository):
    """Concrete repository for Session persistence via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    def _to_domain(self, orm: SessionModel) -> Session:
        """Map a SessionModel ORM instance to a domain entity.

        Args:
            orm: The ORM model instance (with activated_roles loaded).

        Returns:
            The corresponding domain entity.
        """
        role_ids = tuple(sr.role_id for sr in orm.activated_roles)
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
        """Persist a new session.

        Args:
            session: The domain session to persist.

        Returns:
            The persisted session.
        """
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
        """Retrieve a session by its UUID, eager-loading activated roles.

        Args:
            session_id: The session's UUID.

        Returns:
            The session if found, or None.
        """
        stmt = (
            select(SessionModel)
            .options(selectinload(SessionModel.activated_roles))
            .where(SessionModel.id == session_id)
        )
        result = await self._session.execute(stmt)
        orm = result.unique().scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_refresh_token_hash(self, token_hash: str) -> Session | None:
        """Retrieve a session by its refresh token SHA-256 hash.

        Args:
            token_hash: The SHA-256 hex digest of the refresh token.

        Returns:
            The session if found, or None.
        """
        stmt = (
            select(SessionModel)
            .options(selectinload(SessionModel.activated_roles))
            .where(SessionModel.refresh_token_hash == token_hash)
        )
        result = await self._session.execute(stmt)
        orm = result.unique().scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def update(self, session: Session) -> None:
        """Update a session's refresh token hash and revocation status.

        Args:
            session: The domain session with updated fields.
        """
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
        """Revoke all active sessions for an identity.

        Args:
            identity_id: The identity whose sessions to revoke.

        Returns:
            List of revoked session IDs (for cache invalidation).
        """
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
        """Count non-revoked, non-expired sessions for an identity.

        Args:
            identity_id: The identity to count sessions for.

        Returns:
            The number of active sessions.
        """
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
        """Retrieve IDs of all active sessions for an identity.

        Args:
            identity_id: The identity to query.

        Returns:
            List of active session UUIDs.
        """
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
        """Activate roles for a session by inserting session_roles rows.

        Args:
            session_id: The session to add roles to.
            role_ids: The role IDs to activate. If empty, this is a no-op.
        """
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
        """Remove a role from a session's activated roles.

        Args:
            session_id: The session to remove the role from.
            role_id: The role ID to deactivate.
        """
        stmt = delete(SessionRoleModel).where(
            SessionRoleModel.session_id == session_id,
            SessionRoleModel.role_id == role_id,
        )
        await self._session.execute(stmt)

    async def get_active_session_ids_bulk(
        self,
        identity_ids: list[uuid.UUID],
    ) -> list[uuid.UUID]:
        """Retrieve IDs of all active sessions for multiple identities in one query.

        Args:
            identity_ids: The identities to query.

        Returns:
            List of active session UUIDs across all given identities.
        """
        if not identity_ids:
            return []
        now = datetime.now(UTC)
        stmt = select(SessionModel.id).where(
            SessionModel.identity_id.in_(identity_ids),
            SessionModel.is_revoked.is_(False),
            SessionModel.expires_at > now,
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def revoke_oldest_active(self, identity_id: uuid.UUID) -> uuid.UUID | None:
        """Revoke the oldest active session to make room for a new one.

        Args:
            identity_id: The identity whose oldest session to revoke.

        Returns:
            The revoked session ID for cache invalidation, or None if no active session.
        """
        now = datetime.now(UTC)
        stmt = (
            select(SessionModel.id)
            .where(
                SessionModel.identity_id == identity_id,
                SessionModel.is_revoked.is_(False),
                SessionModel.expires_at > now,
            )
            .order_by(SessionModel.created_at.asc())
            .limit(1)
        )
        session_id = (await self._session.execute(stmt)).scalar_one_or_none()
        if session_id is None:
            return None
        await self._session.execute(
            update(SessionModel)
            .where(SessionModel.id == session_id)
            .values(is_revoked=True)
        )
        return session_id
