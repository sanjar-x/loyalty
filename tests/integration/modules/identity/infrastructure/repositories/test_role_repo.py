# tests/integration/modules/identity/infrastructure/repositories/test_role_repo.py
"""Integration tests for RoleRepository — CRUD, assignment, and identity-role linkage."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Identity, Role
from src.modules.identity.domain.value_objects import IdentityType
from src.modules.identity.infrastructure.repositories.identity_repository import (
    IdentityRepository,
)
from src.modules.identity.infrastructure.repositories.role_repository import (
    RoleRepository,
)


def _make_role(name: str = "editor", description: str | None = "Can edit") -> Role:
    return Role(id=uuid.uuid4(), name=name, description=description, is_system=False)


async def test_add_and_get_role(db_session: AsyncSession):
    repo = RoleRepository(session=db_session)
    role = _make_role()

    added = await repo.add(role)
    await db_session.flush()

    fetched = await repo.get(role.id)
    assert fetched is not None
    assert fetched.id == added.id
    assert fetched.name == "editor"
    assert fetched.description == "Can edit"
    assert fetched.is_system is False


async def test_get_returns_none_for_missing(db_session: AsyncSession):
    repo = RoleRepository(session=db_session)
    assert await repo.get(uuid.uuid4()) is None


async def test_get_by_name(db_session: AsyncSession):
    repo = RoleRepository(session=db_session)
    role = _make_role(name="admin-unique")
    await repo.add(role)
    await db_session.flush()

    found = await repo.get_by_name("admin-unique")
    assert found is not None
    assert found.id == role.id

    not_found = await repo.get_by_name("nonexistent")
    assert not_found is None


async def test_delete_role(db_session: AsyncSession):
    repo = RoleRepository(session=db_session)
    role = _make_role(name="to-delete")
    await repo.add(role)
    await db_session.flush()

    await repo.delete(role.id)
    await db_session.flush()

    assert await repo.get(role.id) is None


async def test_get_all_ordered_by_name(db_session: AsyncSession):
    repo = RoleRepository(session=db_session)
    await repo.add(_make_role(name="zz-role"))
    await repo.add(_make_role(name="aa-role"))
    await repo.add(_make_role(name="mm-role"))
    await db_session.flush()

    roles = await repo.get_all()
    names = [r.name for r in roles]
    assert names == sorted(names)


async def test_assign_and_get_identity_role_ids(db_session: AsyncSession):
    identity_repo = IdentityRepository(session=db_session)
    role_repo = RoleRepository(session=db_session)

    identity = Identity.register(IdentityType.LOCAL)
    await identity_repo.add(identity)
    role1 = _make_role(name="role-a")
    role2 = _make_role(name="role-b")
    await role_repo.add(role1)
    await role_repo.add(role2)
    await db_session.flush()

    await role_repo.assign_to_identity(identity.id, role1.id)
    await role_repo.assign_to_identity(identity.id, role2.id)
    await db_session.flush()

    role_ids = await role_repo.get_identity_role_ids(identity.id)
    assert set(role_ids) == {role1.id, role2.id}


async def test_revoke_from_identity(db_session: AsyncSession):
    identity_repo = IdentityRepository(session=db_session)
    role_repo = RoleRepository(session=db_session)

    identity = Identity.register(IdentityType.LOCAL)
    await identity_repo.add(identity)
    role = _make_role(name="revocable")
    await role_repo.add(role)
    await db_session.flush()

    await role_repo.assign_to_identity(identity.id, role.id)
    await db_session.flush()

    await role_repo.revoke_from_identity(identity.id, role.id)
    await db_session.flush()

    role_ids = await role_repo.get_identity_role_ids(identity.id)
    assert role.id not in role_ids


async def test_get_identity_role_ids_empty(db_session: AsyncSession):
    identity_repo = IdentityRepository(session=db_session)
    role_repo = RoleRepository(session=db_session)

    identity = Identity.register(IdentityType.LOCAL)
    await identity_repo.add(identity)
    await db_session.flush()

    role_ids = await role_repo.get_identity_role_ids(identity.id)
    assert role_ids == []
