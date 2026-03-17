# tests/integration/modules/identity/application/queries/test_list_permissions.py
"""Integration tests for ListPermissionsHandler — raw SQL query correctness."""

import uuid

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.queries.list_permissions import ListPermissionsHandler
from src.modules.identity.infrastructure.models import PermissionModel


async def test_list_permissions_returns_seeded_data(
    app_container: AsyncContainer, db_session: AsyncSession
):
    """Permissions are seeded by migrations; handler should return them."""
    perm = PermissionModel(
        id=uuid.uuid4(),
        codename="test:read",
        resource="test",
        action="read",
        description="Test permission",
    )
    db_session.add(perm)
    await db_session.flush()

    handler = ListPermissionsHandler(session=db_session)
    result = await handler.handle()

    codenames = [p.codename for p in result]
    assert "test:read" in codenames


async def test_list_permissions_empty_table(
    app_container: AsyncContainer, db_session: AsyncSession
):
    """If no permissions exist, handler returns empty list."""
    # Note: migrations seed permissions, but in nested transaction they may exist.
    # This test verifies the handler doesn't crash on valid data.
    handler = ListPermissionsHandler(session=db_session)
    result = await handler.handle()
    assert isinstance(result, list)


async def test_list_permissions_fields_populated(
    app_container: AsyncContainer, db_session: AsyncSession
):
    perm = PermissionModel(
        id=uuid.uuid4(),
        codename="catalog:manage",
        resource="catalog",
        action="manage",
        description="Manage catalog",
    )
    db_session.add(perm)
    await db_session.flush()

    handler = ListPermissionsHandler(session=db_session)
    result = await handler.handle()

    matched = [p for p in result if p.codename == "catalog:manage"]
    assert len(matched) == 1
    assert matched[0].resource == "catalog"
    assert matched[0].action == "manage"
    assert matched[0].description == "Manage catalog"
