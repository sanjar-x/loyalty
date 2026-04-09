"""Admin IAM API endpoints for the Identity module.

Provides role and permission management endpoints restricted to identities
with the ``roles:manage`` or ``identities:manage`` permission. Includes CRUD
for roles, identity-role assignment/revocation, identity listing, deactivation,
reactivation, role detail, and grouped permissions.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.identity.application.commands.admin_deactivate_identity import (
    AdminDeactivateIdentityCommand,
    AdminDeactivateIdentityHandler,
)
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
from src.modules.identity.application.commands.reactivate_identity import (
    ReactivateIdentityCommand,
    ReactivateIdentityHandler,
)
from src.modules.identity.application.commands.revoke_role import (
    RevokeRoleCommand,
    RevokeRoleHandler,
)
from src.modules.identity.application.commands.set_role_permissions import (
    SetRolePermissionsCommand,
    SetRolePermissionsHandler,
)
from src.modules.identity.application.commands.update_role import (
    UpdateRoleCommand,
    UpdateRoleHandler,
)
from src.modules.identity.application.queries.get_identity_detail import (
    GetIdentityDetailHandler,
    GetIdentityDetailQuery,
)
from src.modules.identity.application.queries.get_role_detail import (
    GetRoleDetailHandler,
    GetRoleDetailQuery,
)
from src.modules.identity.application.queries.list_identities import (
    ListIdentitiesHandler,
    ListIdentitiesQuery,
)
from src.modules.identity.application.queries.list_permissions import (
    ListPermissionsHandler,
)
from src.modules.identity.application.queries.list_roles import (
    ListRolesHandler,
    RoleWithPermissions,
)
from src.modules.identity.presentation.dependencies import Auth, RequirePermission
from src.modules.identity.presentation.schemas import (
    AdminDeactivateRequest,
    AdminIdentityDetailResponse,
    AdminIdentityListResponse,
    AdminIdentityResponse,
    AssignRoleRequest,
    CreateRoleRequest,
    CreateRoleResponse,
    MessageResponse,
    PermissionDetailResponse,
    PermissionGroupResponse,
    RoleDetailResponse,
    RoleInfoResponse,
    SetRolePermissionsRequest,
    UpdateRoleRequest,
)

admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin — IAM"],
    route_class=DishkaRoute,
)


# ---------------------------------------------------------------------------
# Identity management endpoints
# ---------------------------------------------------------------------------


@admin_router.get(
    "/identities",
    response_model=AdminIdentityListResponse,
    summary="List all identities (paginated)",
    dependencies=[Depends(RequirePermission("identities:manage"))],
)
async def list_identities(
    handler: FromDishka[ListIdentitiesHandler],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    role_id: uuid.UUID | None = None,
    is_active: bool | None = Query(None),
    sort_by: str = Query("created_at", pattern=r"^(created_at|email|last_name)$"),
    sort_order: str = Query("desc", pattern=r"^(asc|desc)$"),
) -> AdminIdentityListResponse:
    """List all identities with pagination, search, and filtering.

    Args:
        handler: The list-identities query handler.
        offset: Pagination offset.
        limit: Page size (1-100).
        search: Optional ILIKE search on email, first_name, last_name.
        role_id: Optional filter by role UUID.
        is_active: Optional filter by active status.
        sort_by: Sort column (created_at, email, last_name).
        sort_order: Sort direction (asc, desc).

    Returns:
        Paginated list of identities with role names.
    """
    query = ListIdentitiesQuery(
        offset=offset,
        limit=limit,
        search=search,
        role_id=role_id,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await handler.handle(query)
    return AdminIdentityListResponse(
        items=[
            AdminIdentityResponse.model_validate(item, from_attributes=True)
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@admin_router.get(
    "/identities/{identity_id}",
    response_model=AdminIdentityDetailResponse,
    summary="Get identity detail",
    dependencies=[Depends(RequirePermission("identities:manage"))],
)
async def get_identity_detail(
    identity_id: uuid.UUID,
    handler: FromDishka[GetIdentityDetailHandler],
) -> AdminIdentityDetailResponse:
    """Get a single identity's full detail with roles.

    Args:
        identity_id: The identity's UUID.
        handler: The get-identity-detail query handler.

    Returns:
        Full identity detail with roles.
    """
    query = GetIdentityDetailQuery(identity_id=identity_id)
    result = await handler.handle(query)
    return AdminIdentityDetailResponse(
        identity_id=result.identity_id,
        email=result.email,
        auth_type=result.auth_type,
        is_active=result.is_active,
        first_name=result.first_name,
        last_name=result.last_name,
        phone=result.phone,
        roles=[
            RoleInfoResponse.model_validate(r, from_attributes=True)
            for r in result.roles
        ],
        created_at=result.created_at,
        deactivated_at=result.deactivated_at,
        deactivated_by=result.deactivated_by,
    )


@admin_router.post(
    "/identities/{identity_id}/deactivate",
    response_model=MessageResponse,
    summary="Admin deactivate identity",
    dependencies=[Depends(RequirePermission("identities:manage"))],
)
async def admin_deactivate_identity(
    identity_id: uuid.UUID,
    body: AdminDeactivateRequest,
    handler: FromDishka[AdminDeactivateIdentityHandler],
    auth: Auth,
) -> MessageResponse:
    """Deactivate an identity as an admin.

    Args:
        identity_id: The target identity's UUID.
        body: The deactivation request payload.
        handler: The admin deactivate identity command handler.
        auth: The authenticated admin context.

    Returns:
        A confirmation message.
    """
    command = AdminDeactivateIdentityCommand(
        identity_id=identity_id,
        reason=body.reason,
        deactivated_by=auth.identity_id,
    )
    await handler.handle(command)
    return MessageResponse(message="Identity deactivated")


@admin_router.post(
    "/identities/{identity_id}/reactivate",
    response_model=MessageResponse,
    summary="Admin reactivate identity",
    dependencies=[Depends(RequirePermission("identities:manage"))],
)
async def admin_reactivate_identity(
    identity_id: uuid.UUID,
    handler: FromDishka[ReactivateIdentityHandler],
    auth: Auth,
) -> MessageResponse:
    """Reactivate a deactivated identity.

    Args:
        identity_id: The target identity's UUID.
        handler: The reactivate identity command handler.
        auth: The authenticated admin context.

    Returns:
        A confirmation message.
    """
    command = ReactivateIdentityCommand(
        identity_id=identity_id,
        reactivated_by=auth.identity_id,
    )
    await handler.handle(command)
    return MessageResponse(message="Identity reactivated")


# ---------------------------------------------------------------------------
# Role management endpoints
# ---------------------------------------------------------------------------


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


@admin_router.get(
    "/roles/{role_id}",
    response_model=RoleDetailResponse,
    summary="Get role detail with permissions",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def get_role_detail(
    role_id: uuid.UUID,
    handler: FromDishka[GetRoleDetailHandler],
) -> RoleDetailResponse:
    """Get a single role's full detail with permissions.

    Args:
        role_id: The role's UUID.
        handler: The get-role-detail query handler.

    Returns:
        Full role detail with permissions.
    """
    query = GetRoleDetailQuery(role_id=role_id)
    result = await handler.handle(query)
    return RoleDetailResponse.model_validate(result, from_attributes=True)


@admin_router.patch(
    "/roles/{role_id}",
    response_model=RoleDetailResponse,
    summary="Update role name/description",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def update_role(
    role_id: uuid.UUID,
    body: UpdateRoleRequest,
    handler: FromDishka[UpdateRoleHandler],
    detail_handler: FromDishka[GetRoleDetailHandler],
) -> RoleDetailResponse:
    """Update a role's name and/or description.

    Args:
        role_id: The role's UUID.
        body: The update role request payload.
        handler: The update-role command handler.
        detail_handler: The get-role-detail query handler for response building.

    Returns:
        The updated role detail.
    """
    command = UpdateRoleCommand(
        role_id=role_id,
        name=body.name,
        description=body.description,
    )
    result = await handler.handle(command)
    detail = await detail_handler.handle(GetRoleDetailQuery(role_id=result.role_id))
    return RoleDetailResponse(
        id=detail.id,
        name=detail.name,
        description=detail.description,
        is_system=detail.is_system,
        permissions=[
            PermissionDetailResponse(**p.model_dump()) for p in detail.permissions
        ],
    )


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


@admin_router.put(
    "/roles/{role_id}/permissions",
    response_model=RoleDetailResponse,
    summary="Set role permissions (full replace)",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def set_role_permissions(
    role_id: uuid.UUID,
    body: SetRolePermissionsRequest,
    handler: FromDishka[SetRolePermissionsHandler],
    detail_handler: FromDishka[GetRoleDetailHandler],
    auth: Auth,
) -> RoleDetailResponse:
    """Set role permissions (full replace). Clears existing and sets new.

    Args:
        role_id: The role's UUID.
        body: The set role permissions request payload.
        handler: The set-role-permissions command handler.
        detail_handler: The get-role-detail query handler for response building.
        auth: The authenticated admin context.

    Returns:
        The updated role detail.
    """
    command = SetRolePermissionsCommand(
        role_id=role_id,
        permission_ids=body.permission_ids,
        session_id=auth.session_id,
    )
    await handler.handle(command)
    detail = await detail_handler.handle(GetRoleDetailQuery(role_id=role_id))
    return RoleDetailResponse(
        id=detail.id,
        name=detail.name,
        description=detail.description,
        is_system=detail.is_system,
        permissions=[
            PermissionDetailResponse(**p.model_dump()) for p in detail.permissions
        ],
    )


# ---------------------------------------------------------------------------
# Permission endpoints
# ---------------------------------------------------------------------------


@admin_router.get(
    "/permissions",
    response_model=list[PermissionGroupResponse],
    summary="List all permissions (grouped by resource)",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def list_permissions(
    handler: FromDishka[ListPermissionsHandler],
) -> list[PermissionGroupResponse]:
    """List all available RBAC permissions grouped by resource.

    Args:
        handler: The list-permissions query handler.

    Returns:
        List of permission groups sorted by resource.
    """
    groups = await handler.handle()
    return [
        PermissionGroupResponse.model_validate(g, from_attributes=True) for g in groups
    ]


# ---------------------------------------------------------------------------
# Identity-Role assignment endpoints
# ---------------------------------------------------------------------------


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
    auth: Auth,
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
