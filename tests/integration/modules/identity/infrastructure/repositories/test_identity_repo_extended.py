# tests/integration/modules/identity/infrastructure/repositories/test_identity_repo_extended.py
"""Extended integration tests for IdentityRepository — credentials, get_by_email, update."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Identity, LocalCredentials
from src.modules.identity.domain.value_objects import IdentityType
from src.modules.identity.infrastructure.repositories.identity_repository import (
    IdentityRepository,
)


async def _seed_identity_with_creds(
    db_session: AsyncSession,
    email: str = "test@example.com",
    password_hash: str = "hashed-pw",
) -> tuple[Identity, LocalCredentials]:
    repo = IdentityRepository(session=db_session)
    identity = Identity.register(IdentityType.LOCAL)
    await repo.add(identity)
    await db_session.flush()

    now = datetime.now(UTC)
    creds = LocalCredentials(
        identity_id=identity.id,
        email=email,
        password_hash=password_hash,
        created_at=now,
        updated_at=now,
    )
    await repo.add_credentials(creds)
    await db_session.flush()
    return identity, creds


async def test_add_credentials_and_get_by_email(db_session: AsyncSession):
    identity, creds = await _seed_identity_with_creds(db_session, email="cred@test.com")

    repo = IdentityRepository(session=db_session)
    result = await repo.get_by_email("cred@test.com")

    assert result is not None
    returned_identity, returned_creds = result
    assert returned_identity.id == identity.id
    assert returned_creds.email == "cred@test.com"
    assert returned_creds.password_hash == "hashed-pw"


async def test_get_by_email_not_found(db_session: AsyncSession):
    repo = IdentityRepository(session=db_session)
    result = await repo.get_by_email("nobody@example.com")
    assert result is None


async def test_update_credentials(db_session: AsyncSession):
    identity, creds = await _seed_identity_with_creds(
        db_session, email="update@test.com", password_hash="old-hash"
    )

    repo = IdentityRepository(session=db_session)
    creds.password_hash = "new-hash"
    await repo.update_credentials(creds)
    await db_session.flush()

    result = await repo.get_by_email("update@test.com")
    assert result is not None
    _, updated_creds = result
    assert updated_creds.password_hash == "new-hash"


async def test_email_exists_false_for_nonexistent(db_session: AsyncSession):
    repo = IdentityRepository(session=db_session)
    assert await repo.email_exists("ghost@nowhere.com") is False


async def test_get_returns_none_for_missing_id(db_session: AsyncSession):
    repo = IdentityRepository(session=db_session)
    assert await repo.get(uuid.uuid4()) is None
