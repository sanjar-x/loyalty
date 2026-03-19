# tests/integration/modules/user/infrastructure/repositories/test_user_repo.py
"""Integration tests for UserRepository — CRUD, profile update, anonymization round-trip."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Identity
from src.modules.identity.domain.value_objects import IdentityType
from src.modules.identity.infrastructure.repositories.identity_repository import (
    IdentityRepository,
)
from src.modules.user.domain.entities import User
from src.modules.user.infrastructure.repositories.user_repository import (
    UserRepository,
)


async def _seed_identity(db_session: AsyncSession) -> Identity:
    """User shares PK with Identity, so we must create an Identity first."""
    repo = IdentityRepository(session=db_session)
    identity = Identity.register(IdentityType.LOCAL)
    await repo.add(identity)
    await db_session.flush()
    return identity


async def test_add_and_get_user(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = UserRepository(session=db_session)

    user = User.create_from_identity(identity_id=identity.id, profile_email="john@example.com")
    added = await repo.add(user)
    await db_session.flush()

    fetched = await repo.get(identity.id)
    assert fetched is not None
    assert fetched.id == added.id
    assert fetched.profile_email == "john@example.com"
    assert fetched.first_name == ""
    assert fetched.last_name == ""
    assert fetched.phone is None


async def test_get_returns_none_for_missing(db_session: AsyncSession):
    repo = UserRepository(session=db_session)
    assert await repo.get(uuid.uuid4()) is None


async def test_update_profile(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = UserRepository(session=db_session)

    user = User.create_from_identity(identity_id=identity.id, profile_email="update@test.com")
    await repo.add(user)
    await db_session.flush()

    user.update_profile(first_name="John", last_name="Doe", phone="+1234567890")
    await repo.update(user)
    await db_session.flush()

    # Expire to force re-fetch from DB
    db_session.expire_all()

    fetched = await repo.get(identity.id)
    assert fetched is not None
    assert fetched.first_name == "John"
    assert fetched.last_name == "Doe"
    assert fetched.phone == "+1234567890"
    assert fetched.profile_email == "update@test.com"


async def test_anonymize_user_round_trip(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = UserRepository(session=db_session)

    user = User.create_from_identity(identity_id=identity.id, profile_email="gdpr@test.com")
    user.update_profile(first_name="Jane", last_name="Smith", phone="+9876543210")
    await repo.add(user)
    await db_session.flush()

    # Anonymize
    user.anonymize()
    await repo.update(user)
    await db_session.flush()

    db_session.expire_all()

    fetched = await repo.get(identity.id)
    assert fetched is not None
    assert fetched.first_name == "[DELETED]"
    assert fetched.last_name == "[DELETED]"
    assert fetched.phone is None
    assert fetched.profile_email is None


async def test_add_user_without_email(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = UserRepository(session=db_session)

    user = User.create_from_identity(identity_id=identity.id)
    await repo.add(user)
    await db_session.flush()

    fetched = await repo.get(identity.id)
    assert fetched is not None
    assert fetched.profile_email is None
