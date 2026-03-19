# tests/integration/modules/identity/infrastructure/repositories/test_identity_repo.py
"""Integration tests for IdentityRepository — Data Mapper correctness."""

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.commands.register import (
    RegisterCommand,
    RegisterHandler,
)
from src.modules.identity.domain.entities import Identity
from src.modules.identity.domain.interfaces import IIdentityRepository
from src.modules.identity.domain.value_objects import IdentityType
from src.modules.identity.infrastructure.models import IdentityModel


async def test_add_identity_persists_to_db(app_container: AsyncContainer, db_session: AsyncSession):
    async with app_container() as request:
        repo = await request.get(IIdentityRepository)
        identity = Identity.register(IdentityType.LOCAL)
        await repo.add(identity)
        await db_session.flush()

    orm = await db_session.get(IdentityModel, identity.id)
    assert orm is not None
    assert orm.type == IdentityType.LOCAL.value


async def test_get_identity_returns_domain_entity(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        repo = await request.get(IIdentityRepository)
        identity = Identity.register(IdentityType.LOCAL)
        await repo.add(identity)
        await db_session.flush()

        result = await repo.get(identity.id)

    assert result is not None
    assert result.id == identity.id
    assert result.is_active is True


async def test_email_exists_returns_true_for_existing(
    app_container: AsyncContainer, db_session: AsyncSession
):
    """Register via handler to get credentials, then check email_exists."""
    async with app_container() as request:
        handler = await request.get(RegisterHandler)
        await handler.handle(RegisterCommand(email="exists@example.com", password="S3cure!Pass"))

    async with app_container() as request:
        repo = await request.get(IIdentityRepository)
        assert await repo.email_exists("exists@example.com") is True
        assert await repo.email_exists("nope@example.com") is False
