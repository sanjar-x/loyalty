# tests/integration/modules/identity/infrastructure/repositories/test_linked_account_repo.py
"""Integration tests for LinkedAccountRepository — OIDC provider linking."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Identity, LinkedAccount
from src.modules.identity.domain.value_objects import IdentityType
from src.modules.identity.infrastructure.repositories.identity_repository import (
    IdentityRepository,
)
from src.modules.identity.infrastructure.repositories.linked_account_repository import (
    LinkedAccountRepository,
)


def _make_account(identity_id: uuid.UUID, provider: str = "google", sub: str = "sub-123") -> LinkedAccount:
    return LinkedAccount(
        id=uuid.uuid4(),
        identity_id=identity_id,
        provider=provider,
        provider_sub_id=sub,
        provider_email=f"{sub}@{provider}.com",
    )


async def _seed_identity(db_session: AsyncSession) -> Identity:
    repo = IdentityRepository(session=db_session)
    identity = Identity.register(IdentityType.OIDC)
    await repo.add(identity)
    await db_session.flush()
    return identity


async def test_add_and_get_by_provider(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = LinkedAccountRepository(session=db_session)

    account = _make_account(identity.id, provider="google", sub="g-001")
    added = await repo.add(account)
    await db_session.flush()

    found = await repo.get_by_provider("google", "g-001")
    assert found is not None
    assert found.id == added.id
    assert found.identity_id == identity.id
    assert found.provider_email == "g-001@google.com"


async def test_get_by_provider_not_found(db_session: AsyncSession):
    repo = LinkedAccountRepository(session=db_session)
    result = await repo.get_by_provider("github", "nonexistent")
    assert result is None


async def test_get_all_for_identity(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = LinkedAccountRepository(session=db_session)

    await repo.add(_make_account(identity.id, provider="google", sub="g-100"))
    await repo.add(_make_account(identity.id, provider="github", sub="gh-200"))
    await db_session.flush()

    accounts = await repo.get_all_for_identity(identity.id)
    assert len(accounts) == 2
    providers = {a.provider for a in accounts}
    assert providers == {"google", "github"}


async def test_get_all_for_identity_empty(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = LinkedAccountRepository(session=db_session)

    accounts = await repo.get_all_for_identity(identity.id)
    assert accounts == []
