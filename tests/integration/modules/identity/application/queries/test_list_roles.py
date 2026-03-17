# tests/integration/modules/identity/application/queries/test_list_roles.py
"""Integration tests for ListRolesHandler — raw SQL query with permissions join."""

import uuid

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.queries.list_roles import ListRolesHandler
from src.modules.identity.infrastructure.models import (
    PermissionModel,
    RoleModel,
    RolePermissionModel,
)


async def test_list_roles_returns_role_with_permissions(
    app_container: AsyncContainer, db_session: AsyncSession
):
    role_id = uuid.uuid4()
    perm_id = uuid.uuid4()

    role = RoleModel(id=role_id, name="test_viewer", description="Test role", is_system=False)
    perm = PermissionModel(
        id=perm_id, codename="test:view", resource="test", action="view", description=None
    )
    db_session.add_all([role, perm])
    await db_session.flush()

    rp = RolePermissionModel(role_id=role_id, permission_id=perm_id)
    db_session.add(rp)
    await db_session.flush()

    handler = ListRolesHandler(session=db_session)
    result = await handler.handle()

    matched = [r for r in result if r.name == "test_viewer"]
    assert len(matched) == 1
    assert matched[0].description == "Test role"
    assert matched[0].is_system is False
    assert "test:view" in matched[0].permissions


async def test_list_roles_empty_permissions(
    app_container: AsyncContainer, db_session: AsyncSession
):
    role = RoleModel(id=uuid.uuid4(), name="empty_role", description=None, is_system=False)
    db_session.add(role)
    await db_session.flush()

    handler = ListRolesHandler(session=db_session)
    result = await handler.handle()

    matched = [r for r in result if r.name == "empty_role"]
    assert len(matched) == 1
    assert matched[0].permissions == []


async def test_list_roles_ordered_by_name(app_container: AsyncContainer, db_session: AsyncSession):
    db_session.add_all(
        [
            RoleModel(id=uuid.uuid4(), name="zz_last_role", is_system=False),
            RoleModel(id=uuid.uuid4(), name="aa_first_role", is_system=False),
        ]
    )
    await db_session.flush()

    handler = ListRolesHandler(session=db_session)
    result = await handler.handle()

    names = [r.name for r in result]
    aa_idx = names.index("aa_first_role")
    zz_idx = names.index("zz_last_role")
    assert aa_idx < zz_idx
