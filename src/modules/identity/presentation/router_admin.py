"""Admin IAM API endpoints for the Identity module.

Provides role and permission management endpoints restricted to identities
with the ``roles:manage`` permission. Includes CRUD for roles and
identity-role assignment/revocation.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status

from src.modules.identity.application.commands.assign_role import (
    AssignRoleCommand,
    AssignRoleHandler,
)
from src.modules.identity.application.commands.create_role import (
    CreateRoleCommand,
    CreateRoleHandler,
)
from src.modules.identity.application.commands.delete_role import (
    DeleteRoleCommand,
    DeleteRoleHandler,
)
from src.modules.identity.application.commands.revoke_role import (
    RevokeRoleCommand,
    RevokeRoleHandler,
)
from src.modules.identity.application.queries.list_permissions import (
    ListPermissionsHandler,
    PermissionInfo,
)
from src.modules.identity.application.queries.list_roles import (
    ListRolesHandler,
    RoleWithPermissions,
)
from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_auth_context,
)
from src.modules.identity.presentation.schemas import (
    AssignRoleRequest,
    CreateRoleRequest,
    CreateRoleResponse,
    MessageResponse,
)
from src.shared.interfaces.auth import AuthContext

admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin — IAM"],
    route_class=DishkaRoute,
)


@admin_router.get(
    "/roles",
    response_model=list[RoleWithPermissions],
    summary="List all roles with permissions",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def list_roles(
    handler: FromDishka[ListRolesHandler],
) -> list[RoleWithPermissions]:
    """List all RBAC roles with their associated permission codenames.

    Args:
        handler: The list-roles query handler.

    Returns:
        List of roles with their permissions.
    """
    return await handler.handle()


@admin_router.post(
    "/roles",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateRoleResponse,
    summary="Create a custom role",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def create_role(
    body: CreateRoleRequest,
    handler: FromDishka[CreateRoleHandler],
) -> CreateRoleResponse:
    """Create a new custom (non-system) role.

    Args:
        body: The role creation request payload.
        handler: The create-role command handler.

    Returns:
        The new role's UUID and a confirmation message.
    """
    command = CreateRoleCommand(name=body.name, description=body.description)
    result = await handler.handle(command)
    return CreateRoleResponse(role_id=result.role_id)


@admin_router.delete(
    "/roles/{role_id}",
    response_model=MessageResponse,
    summary="Delete a custom role",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def delete_role(
    role_id: uuid.UUID,
    handler: FromDishka[DeleteRoleHandler],
) -> MessageResponse:
    """Delete a custom role by its UUID. System roles cannot be deleted.

    Args:
        role_id: The UUID of the role to delete.
        handler: The delete-role command handler.

    Returns:
        A confirmation message.
    """
    await handler.handle(DeleteRoleCommand(role_id=role_id))
    return MessageResponse(message="Role deleted")


@admin_router.get(
    "/permissions",
    response_model=list[PermissionInfo],
    summary="List all permissions",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def list_permissions(
    handler: FromDishka[ListPermissionsHandler],
) -> list[PermissionInfo]:
    """List all available RBAC permissions.

    Args:
        handler: The list-permissions query handler.

    Returns:
        List of all permission definitions.
    """
    return await handler.handle()


@admin_router.post(
    "/identities/{identity_id}/roles",
    response_model=MessageResponse,
    summary="Assign role to identity",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def assign_role(
    identity_id: uuid.UUID,
    body: AssignRoleRequest,
    handler: FromDishka[AssignRoleHandler],
    auth: AuthContext = Depends(get_auth_context),
) -> MessageResponse:
    """Assign a role to an identity.

    Args:
        identity_id: The target identity's UUID.
        body: The role assignment request payload.
        handler: The assign-role command handler.
        auth: The authenticated admin context.

    Returns:
        A confirmation message.
    """
    command = AssignRoleCommand(
        identity_id=identity_id,
        role_id=body.role_id,
        assigned_by=auth.identity_id,
    )
    await handler.handle(command)
    return MessageResponse(message="Role assigned")


@admin_router.delete(
    "/identities/{identity_id}/roles/{role_id}",
    response_model=MessageResponse,
    summary="Revoke role from identity",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def revoke_role(
    identity_id: uuid.UUID,
    role_id: uuid.UUID,
    handler: FromDishka[RevokeRoleHandler],
) -> MessageResponse:
    """Revoke a role from an identity.

    Args:
        identity_id: The target identity's UUID.
        role_id: The role's UUID to revoke.
        handler: The revoke-role command handler.

    Returns:
        A confirmation message.
    """
    command = RevokeRoleCommand(identity_id=identity_id, role_id=role_id)
    await handler.handle(command)
    return MessageResponse(message="Role revoked")
