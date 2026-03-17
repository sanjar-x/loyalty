# tests/integration/modules/identity/application/queries/test_get_my_sessions.py
"""Integration tests for GetMySessionsHandler — raw SQL query with INET type."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.queries.get_my_sessions import (
    GetMySessionsHandler,
    GetMySessionsQuery,
)
from src.modules.identity.infrastructure.models import IdentityModel, SessionModel


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def test_get_my_sessions_returns_active_sessions(
    app_container: AsyncContainer, db_session: AsyncSession
):
    identity_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(UTC)

    identity = IdentityModel(id=identity_id, type="LOCAL", is_active=True)
    db_session.add(identity)
    await db_session.flush()

    session_model = SessionModel(
        id=session_id,
        identity_id=identity_id,
        refresh_token_hash=_token_hash("token1"),
        ip_address="192.168.1.1",
        user_agent="TestAgent/1.0",
        is_revoked=False,
        expires_at=now + timedelta(days=30),
    )
    db_session.add(session_model)
    await db_session.flush()

    handler = GetMySessionsHandler(session=db_session)
    result = await handler.handle(
        GetMySessionsQuery(identity_id=identity_id, current_session_id=session_id)
    )

    assert len(result) == 1
    assert result[0].id == session_id
    assert result[0].ip_address == "192.168.1.1"
    assert result[0].user_agent == "TestAgent/1.0"
    assert result[0].is_current is True
    assert result[0].is_revoked is False


async def test_get_my_sessions_excludes_revoked(
    app_container: AsyncContainer, db_session: AsyncSession
):
    identity_id = uuid.uuid4()
    now = datetime.now(UTC)

    identity = IdentityModel(id=identity_id, type="LOCAL", is_active=True)
    db_session.add(identity)
    await db_session.flush()

    active_session = SessionModel(
        id=uuid.uuid4(),
        identity_id=identity_id,
        refresh_token_hash=_token_hash("active"),
        is_revoked=False,
        expires_at=now + timedelta(days=30),
    )
    revoked_session = SessionModel(
        id=uuid.uuid4(),
        identity_id=identity_id,
        refresh_token_hash=_token_hash("revoked"),
        is_revoked=True,
        expires_at=now + timedelta(days=30),
    )
    db_session.add_all([active_session, revoked_session])
    await db_session.flush()

    handler = GetMySessionsHandler(session=db_session)
    result = await handler.handle(
        GetMySessionsQuery(identity_id=identity_id, current_session_id=active_session.id)
    )

    assert len(result) == 1
    assert result[0].id == active_session.id


async def test_get_my_sessions_marks_current_session(
    app_container: AsyncContainer, db_session: AsyncSession
):
    identity_id = uuid.uuid4()
    current_id = uuid.uuid4()
    other_id = uuid.uuid4()
    now = datetime.now(UTC)

    identity = IdentityModel(id=identity_id, type="LOCAL", is_active=True)
    db_session.add(identity)
    await db_session.flush()

    db_session.add_all(
        [
            SessionModel(
                id=current_id,
                identity_id=identity_id,
                refresh_token_hash=_token_hash("current"),
                is_revoked=False,
                expires_at=now + timedelta(days=30),
            ),
            SessionModel(
                id=other_id,
                identity_id=identity_id,
                refresh_token_hash=_token_hash("other"),
                is_revoked=False,
                expires_at=now + timedelta(days=30),
            ),
        ]
    )
    await db_session.flush()

    handler = GetMySessionsHandler(session=db_session)
    result = await handler.handle(
        GetMySessionsQuery(identity_id=identity_id, current_session_id=current_id)
    )

    by_id = {s.id: s for s in result}
    assert by_id[current_id].is_current is True
    assert by_id[other_id].is_current is False
