# tests/integration/modules/identity/infrastructure/repositories/test_permission_repo.py
"""Integration tests for PermissionRepository — read-only lookups."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.infrastructure.models import PermissionModel
from src.modules.identity.infrastructure.repositories.permission_repository import (
    PermissionRepository,
)


async def test_get_all_returns_ordered_permissions(db_session: AsyncSession):
    # Seed two permissions (z before a alphabetically)
    p1 = PermissionModel(
        id=uuid.uuid4(),
        codename="catalog:manage",
        resource="catalog",
        action="manage",
        description="Manage catalog",
    )
    p2 = PermissionModel(
        id=uuid.uuid4(),
        codename="admin:access",
        resource="admin",
        action="access",
        description="Admin access",
    )
    db_session.add_all([p1, p2])
    await db_session.flush()

    repo = PermissionRepository(session=db_session)
    result = await repo.get_all()

    assert len(result) >= 2
    codenames = [p.codename for p in result]
    assert codenames == sorted(codenames)


async def test_get_by_codename_found(db_session: AsyncSession):
    perm = PermissionModel(
        id=uuid.uuid4(),
        codename="user:read",
        resource="user",
        action="read",
        description="Read user",
    )
    db_session.add(perm)
    await db_session.flush()

    repo = PermissionRepository(session=db_session)
    found = await repo.get_by_codename("user:read")

    assert found is not None
    assert found.id == perm.id
    assert found.resource == "user"
    assert found.action == "read"


async def test_get_by_codename_not_found(db_session: AsyncSession):
    repo = PermissionRepository(session=db_session)
    result = await repo.get_by_codename("nonexistent:action")
    assert result is None
