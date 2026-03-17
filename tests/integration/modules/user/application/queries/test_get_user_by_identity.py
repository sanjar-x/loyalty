# tests/integration/modules/user/application/queries/test_get_user_by_identity.py
"""Integration tests for GetUserByIdentityHandler — raw SQL query correctness."""

import uuid

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.infrastructure.models import IdentityModel
from src.modules.user.application.queries.get_user_by_identity import (
    GetUserByIdentityHandler,
    GetUserByIdentityQuery,
)
from src.modules.user.infrastructure.models import UserModel


async def test_get_user_by_identity_returns_user_id(
    app_container: AsyncContainer, db_session: AsyncSession
):
    identity_id = uuid.uuid4()

    identity = IdentityModel(id=identity_id, type="LOCAL", is_active=True)
    db_session.add(identity)
    await db_session.flush()

    user = UserModel(id=identity_id, first_name="Test", last_name="User")
    db_session.add(user)
    await db_session.flush()

    handler = GetUserByIdentityHandler(session=db_session)
    result = await handler.handle(GetUserByIdentityQuery(identity_id=identity_id))

    assert result == identity_id


async def test_get_user_by_identity_returns_none_for_missing(
    app_container: AsyncContainer, db_session: AsyncSession
):
    handler = GetUserByIdentityHandler(session=db_session)
    result = await handler.handle(GetUserByIdentityQuery(identity_id=uuid.uuid4()))

    assert result is None
