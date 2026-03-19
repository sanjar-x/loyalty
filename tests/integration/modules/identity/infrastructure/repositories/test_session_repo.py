# tests/integration/modules/identity/infrastructure/repositories/test_session_repo.py
"""Integration tests for SessionRepository."""

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Identity, Session
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    ISessionRepository,
)
from src.modules.identity.domain.value_objects import IdentityType


async def test_add_session_persists_with_hashed_token(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        identity_repo = await request.get(IIdentityRepository)
        session_repo = await request.get(ISessionRepository)

        identity = Identity.register(IdentityType.LOCAL)
        await identity_repo.add(identity)
        await db_session.flush()

        raw_token = "test-refresh-token"
        session = Session.create(
            identity_id=identity.id,
            refresh_token=raw_token,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        await session_repo.add(session)
        await db_session.flush()

        result = await session_repo.get(session.id)

    assert result is not None
    assert result.identity_id == identity.id


async def test_revoke_all_for_identity(app_container: AsyncContainer, db_session: AsyncSession):
    async with app_container() as request:
        identity_repo = await request.get(IIdentityRepository)
        session_repo = await request.get(ISessionRepository)

        identity = Identity.register(IdentityType.LOCAL)
        await identity_repo.add(identity)
        await db_session.flush()

        for i in range(3):
            s = Session.create(
                identity_id=identity.id,
                refresh_token=f"token-{i}",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0",
                role_ids=[],
                expires_days=30,
            )
            await session_repo.add(s)
        await db_session.flush()

        revoked_ids = await session_repo.revoke_all_for_identity(identity.id)

    assert len(revoked_ids) == 3
