# tests/integration/modules/user/application/queries/test_get_my_profile.py
"""Integration tests for GetMyProfileHandler — raw SQL query correctness."""

import uuid

import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.infrastructure.models import IdentityModel
from src.modules.user.application.queries.get_my_profile import (
    GetMyProfileHandler,
    GetMyProfileQuery,
)
from src.modules.user.domain.exceptions import UserNotFoundError
from src.modules.user.infrastructure.models import UserModel


async def test_get_my_profile_returns_user_profile(
    app_container: AsyncContainer, db_session: AsyncSession
):
    identity_id = uuid.uuid4()

    identity = IdentityModel(id=identity_id, type="LOCAL", is_active=True)
    db_session.add(identity)
    await db_session.flush()

    user = UserModel(
        id=identity_id,
        profile_email="user@example.com",
        first_name="John",
        last_name="Doe",
        phone="+1234567890",
    )
    db_session.add(user)
    await db_session.flush()

    handler = GetMyProfileHandler(session=db_session)
    result = await handler.handle(GetMyProfileQuery(user_id=identity_id))

    assert result.id == identity_id
    assert result.profile_email == "user@example.com"
    assert result.first_name == "John"
    assert result.last_name == "Doe"
    assert result.phone == "+1234567890"


async def test_get_my_profile_raises_not_found(
    app_container: AsyncContainer, db_session: AsyncSession
):
    handler = GetMyProfileHandler(session=db_session)

    with pytest.raises(UserNotFoundError):
        await handler.handle(GetMyProfileQuery(user_id=uuid.uuid4()))


async def test_get_my_profile_nullable_fields(
    app_container: AsyncContainer, db_session: AsyncSession
):
    identity_id = uuid.uuid4()

    identity = IdentityModel(id=identity_id, type="LOCAL", is_active=True)
    db_session.add(identity)
    await db_session.flush()

    user = UserModel(
        id=identity_id,
        first_name="Jane",
        last_name="Smith",
        profile_email=None,
        phone=None,
    )
    db_session.add(user)
    await db_session.flush()

    handler = GetMyProfileHandler(session=db_session)
    result = await handler.handle(GetMyProfileQuery(user_id=identity_id))

    assert result.profile_email is None
    assert result.phone is None
    assert result.first_name == "Jane"
