# tests/integration/modules/identity/infrastructure/repositories/test_session_repo_extended.py
"""Extended integration tests for SessionRepository — covers remaining methods."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Identity, Role, Session
from src.modules.identity.domain.value_objects import IdentityType
from src.modules.identity.infrastructure.repositories.identity_repository import (
    IdentityRepository,
)
from src.modules.identity.infrastructure.repositories.role_repository import (
    RoleRepository,
)
from src.modules.identity.infrastructure.repositories.session_repository import (
    SessionRepository,
)


async def _seed_identity(db_session: AsyncSession) -> Identity:
    repo = IdentityRepository(session=db_session)
    identity = Identity.register(IdentityType.LOCAL)
    await repo.add(identity)
    await db_session.flush()
    return identity


async def _create_session(
    session_repo: SessionRepository,
    identity_id: uuid.UUID,
    token: str = "token",
    db_session: AsyncSession | None = None,
) -> Session:
    sess = Session.create(
        identity_id=identity_id,
        refresh_token=token,
        ip_address="127.0.0.1",
        user_agent="TestAgent/1.0",
        role_ids=[],
        expires_days=30,
    )
    await session_repo.add(sess)
    if db_session:
        await db_session.flush()
    return sess


async def test_get_by_refresh_token_hash(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = SessionRepository(session=db_session)

    sess = await _create_session(repo, identity.id, token="unique-rt", db_session=db_session)

    found = await repo.get_by_refresh_token_hash(sess.refresh_token_hash)
    assert found is not None
    assert found.id == sess.id


async def test_get_by_refresh_token_hash_not_found(db_session: AsyncSession):
    repo = SessionRepository(session=db_session)
    result = await repo.get_by_refresh_token_hash("nonexistent-hash")
    assert result is None


async def test_update_session_revoke(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = SessionRepository(session=db_session)

    sess = await _create_session(repo, identity.id, token="update-test", db_session=db_session)
    sess.revoke()

    await repo.update(sess)
    await db_session.flush()

    updated = await repo.get(sess.id)
    assert updated is not None
    assert updated.is_revoked is True


async def test_count_active(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = SessionRepository(session=db_session)

    for i in range(3):
        await _create_session(repo, identity.id, token=f"active-{i}")
    await db_session.flush()

    count = await repo.count_active(identity.id)
    assert count == 3


async def test_count_active_excludes_revoked(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = SessionRepository(session=db_session)

    s1 = await _create_session(repo, identity.id, token="keep")
    s2 = await _create_session(repo, identity.id, token="revoke-me")
    await db_session.flush()

    s2.revoke()
    await repo.update(s2)
    await db_session.flush()

    count = await repo.count_active(identity.id)
    assert count == 1


async def test_get_active_session_ids(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    repo = SessionRepository(session=db_session)

    s1 = await _create_session(repo, identity.id, token="id-1")
    s2 = await _create_session(repo, identity.id, token="id-2")
    await db_session.flush()

    ids = await repo.get_active_session_ids(identity.id)
    assert set(ids) == {s1.id, s2.id}


async def test_add_session_roles(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    role_repo = RoleRepository(session=db_session)
    session_repo = SessionRepository(session=db_session)

    role1 = Role(id=uuid.uuid4(), name="r1-test", description=None, is_system=False)
    role2 = Role(id=uuid.uuid4(), name="r2-test", description=None, is_system=False)
    await role_repo.add(role1)
    await role_repo.add(role2)

    sess = await _create_session(session_repo, identity.id, token="roles-test", db_session=db_session)

    await session_repo.add_session_roles(sess.id, [role1.id, role2.id])
    await db_session.flush()

    reloaded = await session_repo.get(sess.id)
    assert reloaded is not None
    assert set(reloaded.activated_roles) == {role1.id, role2.id}


async def test_add_session_roles_empty_list(db_session: AsyncSession):
    """Passing empty list should be a no-op."""
    identity = await _seed_identity(db_session)
    session_repo = SessionRepository(session=db_session)

    sess = await _create_session(session_repo, identity.id, token="no-roles", db_session=db_session)

    await session_repo.add_session_roles(sess.id, [])
    # Should not raise


async def test_remove_session_role(db_session: AsyncSession):
    identity = await _seed_identity(db_session)
    role_repo = RoleRepository(session=db_session)
    session_repo = SessionRepository(session=db_session)

    role = Role(id=uuid.uuid4(), name="removable", description=None, is_system=False)
    await role_repo.add(role)

    sess = await _create_session(session_repo, identity.id, token="remove-role", db_session=db_session)

    await session_repo.add_session_roles(sess.id, [role.id])
    await db_session.flush()

    await session_repo.remove_session_role(sess.id, role.id)
    await db_session.flush()

    reloaded = await session_repo.get(sess.id)
    assert reloaded is not None
    assert role.id not in reloaded.activated_roles
