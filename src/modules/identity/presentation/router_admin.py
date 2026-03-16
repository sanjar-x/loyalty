# src/modules/identity/presentation/router_admin.py
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
    command = RevokeRoleCommand(identity_id=identity_id, role_id=role_id)
    await handler.handle(command)
    return MessageResponse(message="Role revoked")
