# tests/integration/modules/user/application/commands/test_create_user.py
"""Integration tests for CreateUserHandler."""

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Identity
from src.modules.identity.domain.interfaces import IIdentityRepository
from src.modules.identity.domain.value_objects import IdentityType
from src.modules.user.application.commands.create_user import (
    CreateUserCommand,
    CreateUserHandler,
)
from src.modules.user.infrastructure.models import UserModel


async def _seed_identity(
    app_container: AsyncContainer, db_session: AsyncSession
) -> Identity:
    """Create an Identity row to satisfy the users.id FK constraint."""
    async with app_container() as request:
        repo = await request.get(IIdentityRepository)
        identity = Identity.register(IdentityType.LOCAL)
        await repo.add(identity)
        await db_session.flush()
    return identity


async def test_create_user_from_identity_event(
    app_container: AsyncContainer, db_session: AsyncSession
):
    """Verify CreateUserHandler persists a User row with Shared PK from Identity."""
    identity = await _seed_identity(app_container, db_session)

    async with app_container() as request:
        handler = await request.get(CreateUserHandler)
        await handler.handle(
            CreateUserCommand(identity_id=identity.id, profile_email="new@example.com")
        )

    orm = await db_session.get(UserModel, identity.id)
    assert orm is not None
    assert orm.id == identity.id  # Shared PK with Identity


async def test_create_user_is_idempotent(
    app_container: AsyncContainer, db_session: AsyncSession
):
    """CreateUserHandler should be idempotent — skip if user already exists."""
    identity = await _seed_identity(app_container, db_session)

    # First call — creates user
    async with app_container() as request:
        handler = await request.get(CreateUserHandler)
        await handler.handle(
            CreateUserCommand(identity_id=identity.id, profile_email="idem@example.com")
        )

    # Second call — should not raise, just skip
    async with app_container() as request:
        handler = await request.get(CreateUserHandler)
        await handler.handle(
            CreateUserCommand(identity_id=identity.id, profile_email="idem@example.com")
        )

    orm = await db_session.get(UserModel, identity.id)
    assert orm is not None
