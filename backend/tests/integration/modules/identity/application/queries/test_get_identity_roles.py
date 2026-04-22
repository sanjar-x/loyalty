# tests/integration/modules/identity/application/queries/test_get_identity_roles.py
"""Integration tests for GetIdentityRolesHandler — raw SQL JOIN query."""

import uuid

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.queries.get_identity_roles import (
    GetIdentityRolesHandler,
    GetIdentityRolesQuery,
)
from src.modules.identity.infrastructure.models import (
    IdentityModel,
    IdentityRoleModel,
    RoleModel,
)


async def test_get_identity_roles_returns_assigned_roles(
    app_container: AsyncContainer, db_session: AsyncSession
):
    identity_id = uuid.uuid4()
    role_id = uuid.uuid4()

    identity = IdentityModel(id=identity_id, account_type="CUSTOMER", primary_auth_method="password", is_active=True)
    role = RoleModel(id=role_id, name="test_admin", is_system=False)
    db_session.add_all([identity, role])
    await db_session.flush()

    assignment = IdentityRoleModel(identity_id=identity_id, role_id=role_id)
    db_session.add(assignment)
    await db_session.flush()

    handler = GetIdentityRolesHandler(session=db_session)
    result = await handler.handle(GetIdentityRolesQuery(identity_id=identity_id))

    assert len(result) == 1
    assert result[0].role_name == "test_admin"
    assert result[0].role_id == role_id
    assert result[0].is_system is False


async def test_get_identity_roles_returns_empty_for_no_assignments(
    app_container: AsyncContainer, db_session: AsyncSession
):
    identity_id = uuid.uuid4()
    identity = IdentityModel(id=identity_id, account_type="CUSTOMER", primary_auth_method="password", is_active=True)
    db_session.add(identity)
    await db_session.flush()

    handler = GetIdentityRolesHandler(session=db_session)
    result = await handler.handle(GetIdentityRolesQuery(identity_id=identity_id))

    assert result == []


async def test_get_identity_roles_multiple_roles_ordered(
    app_container: AsyncContainer, db_session: AsyncSession
):
    identity_id = uuid.uuid4()
    role_a_id = uuid.uuid4()
    role_b_id = uuid.uuid4()

    identity = IdentityModel(id=identity_id, account_type="CUSTOMER", primary_auth_method="password", is_active=True)
    role_a = RoleModel(id=role_a_id, name="aaa_role", is_system=False)
    role_b = RoleModel(id=role_b_id, name="zzz_role", is_system=True)
    db_session.add_all([identity, role_a, role_b])
    await db_session.flush()

    db_session.add_all(
        [
            IdentityRoleModel(identity_id=identity_id, role_id=role_a_id),
            IdentityRoleModel(identity_id=identity_id, role_id=role_b_id),
        ]
    )
    await db_session.flush()

    handler = GetIdentityRolesHandler(session=db_session)
    result = await handler.handle(GetIdentityRolesQuery(identity_id=identity_id))

    assert len(result) == 2
    assert result[0].role_name == "aaa_role"
    assert result[1].role_name == "zzz_role"
    assert result[1].is_system is True
