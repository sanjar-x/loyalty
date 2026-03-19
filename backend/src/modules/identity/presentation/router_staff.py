"""Staff management admin router.

Provides endpoints for listing, viewing, deactivating, and reactivating staff
members, as well as managing staff invitations. All endpoints require the
``staff:manage`` or ``staff:invite`` permission.

IMPORTANT: Invitation routes (/invitations*) MUST be registered before the
/{identity_id} catch-all to prevent FastAPI's greedy path matching from
treating "invitations" as a UUID path parameter.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query

from src.modules.identity.application.commands.admin_deactivate_identity import (
    AdminDeactivateIdentityCommand,
    AdminDeactivateIdentityHandler,
)
from src.modules.identity.application.commands.invite_staff import (
    InviteStaffCommand,
    InviteStaffHandler,
)
from src.modules.identity.application.commands.reactivate_identity import (
    ReactivateIdentityCommand,
    ReactivateIdentityHandler,
)
from src.modules.identity.application.commands.revoke_staff_invitation import (
    RevokeStaffInvitationCommand,
    RevokeStaffInvitationHandler,
)
from src.modules.identity.application.queries.get_staff_detail import (
    GetStaffDetailHandler,
    GetStaffDetailQuery,
)
from src.modules.identity.application.queries.list_staff import (
    ListStaffHandler,
    ListStaffQuery,
)
from src.modules.identity.application.queries.list_staff_invitations import (
    ListStaffInvitationsHandler,
    ListStaffInvitationsQuery,
)
from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_auth_context,
)
from src.modules.identity.presentation.schemas import (
    AdminDeactivateRequest,
    InvitationListItemResponse,
    InvitationListResponse,
    InviteStaffRequest,
    InviteStaffResponse,
    MessageResponse,
    RoleInfoResponse,
    StaffDetailResponse,
    StaffListItemResponse,
    StaffListResponse,
)
from src.shared.interfaces.auth import AuthContext

staff_admin_router = APIRouter(
    prefix="/admin/staff",
    tags=["Admin — Staff Management"],
    route_class=DishkaRoute,
)


# ---------------------------------------------------------------------------
# Staff list (no path param — safe before /{identity_id})
# ---------------------------------------------------------------------------


@staff_admin_router.get(
    "",
    response_model=StaffListResponse,
    summary="List staff members (paginated)",
    dependencies=[Depends(RequirePermission("staff:manage"))],
)
async def list_staff(
    handler: FromDishka[ListStaffHandler],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    role_id: uuid.UUID | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: str = Query("created_at", pattern=r"^(created_at|email|last_name)$"),
    sort_order: str = Query("desc", pattern=r"^(asc|desc)$"),
) -> StaffListResponse:
    """List staff members with pagination and filtering.

    Args:
        handler: The list-staff query handler.
        offset: Pagination offset.
        limit: Page size (1-100).
        search: Optional ILIKE search on email, first_name, last_name.
        role_id: Optional filter by role UUID.
        is_active: Optional filter by active status.
        sort_by: Sort column (created_at, email, last_name).
        sort_order: Sort direction (asc, desc).

    Returns:
        Paginated list of staff members with role names.
    """
    result = await handler.handle(
        ListStaffQuery(
            offset=offset,
            limit=limit,
            search=search,
            role_id=role_id,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )
    return StaffListResponse(
        items=[
            StaffListItemResponse(
                identity_id=item.identity_id,
                email=item.email,
                first_name=item.first_name,
                last_name=item.last_name,
                position=item.position,
                department=item.department,
                roles=item.roles,
                is_active=item.is_active,
                created_at=item.created_at,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


# ---------------------------------------------------------------------------
# Staff Invitation endpoints (MUST come before /{identity_id} catch-all)
# ---------------------------------------------------------------------------


@staff_admin_router.post(
    "/invitations",
    response_model=InviteStaffResponse,
    status_code=201,
    summary="Create a staff invitation",
    dependencies=[Depends(RequirePermission("staff:invite"))],
)
async def invite_staff(
    body: InviteStaffRequest,
    handler: FromDishka[InviteStaffHandler],
    auth: AuthContext = Depends(get_auth_context),
) -> InviteStaffResponse:
    """Create a staff invitation.

    Args:
        body: The invitation request payload.
        handler: The invite-staff command handler.
        auth: The authenticated admin context.

    Returns:
        The invitation ID and invite URL.
    """
    result = await handler.handle(
        InviteStaffCommand(
            email=body.email,
            role_ids=body.role_ids,
            invited_by=auth.identity_id,
        )
    )
    return InviteStaffResponse(
        invitation_id=result.invitation_id,
        invite_url=f"/invite/{result.raw_token}",
    )


@staff_admin_router.get(
    "/invitations",
    response_model=InvitationListResponse,
    summary="List staff invitations (paginated)",
    dependencies=[Depends(RequirePermission("staff:manage"))],
)
async def list_invitations(
    handler: FromDishka[ListStaffInvitationsHandler],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern=r"^(PENDING|ACCEPTED|REVOKED|EXPIRED)$"),
) -> InvitationListResponse:
    """List staff invitations with optional status filter.

    Args:
        handler: The list-staff-invitations query handler.
        offset: Pagination offset.
        limit: Page size (1-100).
        status: Optional filter by invitation status.

    Returns:
        Paginated list of staff invitations.
    """
    result = await handler.handle(
        ListStaffInvitationsQuery(offset=offset, limit=limit, status=status)
    )
    return InvitationListResponse(
        items=[
            InvitationListItemResponse(
                id=item.id,
                email=item.email,
                status=item.status,
                invited_by_email=item.invited_by_email,
                roles=item.roles,
                created_at=item.created_at,
                expires_at=item.expires_at,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@staff_admin_router.delete(
    "/invitations/{invitation_id}",
    response_model=MessageResponse,
    summary="Revoke a staff invitation",
    dependencies=[Depends(RequirePermission("staff:manage"))],
)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    handler: FromDishka[RevokeStaffInvitationHandler],
    auth: AuthContext = Depends(get_auth_context),
) -> MessageResponse:
    """Revoke a pending staff invitation.

    Args:
        invitation_id: The invitation's UUID.
        handler: The revoke-staff-invitation command handler.
        auth: The authenticated admin context.

    Returns:
        A confirmation message.
    """
    await handler.handle(
        RevokeStaffInvitationCommand(
            invitation_id=invitation_id,
            revoked_by=auth.identity_id,
        )
    )
    return MessageResponse(message="Invitation revoked")


# ---------------------------------------------------------------------------
# Staff detail + state transitions (/{identity_id} catch-all — MUST be last)
# ---------------------------------------------------------------------------


@staff_admin_router.get(
    "/{identity_id}",
    response_model=StaffDetailResponse,
    summary="Get staff member detail",
    dependencies=[Depends(RequirePermission("staff:manage"))],
)
async def get_staff_detail(
    identity_id: uuid.UUID,
    handler: FromDishka[GetStaffDetailHandler],
) -> StaffDetailResponse:
    """Get full detail for a single staff member.

    Args:
        identity_id: The staff member's identity UUID.
        handler: The get-staff-detail query handler.

    Returns:
        Full staff member detail with roles.
    """
    result = await handler.handle(GetStaffDetailQuery(identity_id=identity_id))
    return StaffDetailResponse(
        identity_id=result.identity_id,
        email=result.email,
        auth_type=result.auth_type,
        is_active=result.is_active,
        first_name=result.first_name,
        last_name=result.last_name,
        position=result.position,
        department=result.department,
        roles=[
            RoleInfoResponse(id=r.id, name=r.name, description=r.description, is_system=r.is_system)
            for r in result.roles
        ],
        created_at=result.created_at,
        deactivated_at=result.deactivated_at,
        deactivated_by=result.deactivated_by,
        invited_by=result.invited_by,
    )


@staff_admin_router.post(
    "/{identity_id}/deactivate",
    response_model=MessageResponse,
    summary="Deactivate a staff member",
    dependencies=[Depends(RequirePermission("staff:manage"))],
)
async def deactivate_staff(
    identity_id: uuid.UUID,
    body: AdminDeactivateRequest,
    handler: FromDishka[AdminDeactivateIdentityHandler],
    auth: AuthContext = Depends(get_auth_context),
) -> MessageResponse:
    """Deactivate a staff member.

    Args:
        identity_id: The target staff member's identity UUID.
        body: The deactivation request payload.
        handler: The admin deactivate identity command handler.
        auth: The authenticated admin context.

    Returns:
        A confirmation message.
    """
    await handler.handle(
        AdminDeactivateIdentityCommand(
            identity_id=identity_id,
            reason=body.reason,
            deactivated_by=auth.identity_id,
        )
    )
    return MessageResponse(message="Staff member deactivated")


@staff_admin_router.post(
    "/{identity_id}/reactivate",
    response_model=MessageResponse,
    summary="Reactivate a staff member",
    dependencies=[Depends(RequirePermission("staff:manage"))],
)
async def reactivate_staff(
    identity_id: uuid.UUID,
    handler: FromDishka[ReactivateIdentityHandler],
    auth: AuthContext = Depends(get_auth_context),
) -> MessageResponse:
    """Reactivate a deactivated staff member.

    Args:
        identity_id: The target staff member's identity UUID.
        handler: The reactivate identity command handler.
        auth: The authenticated admin context.

    Returns:
        A confirmation message.
    """
    await handler.handle(
        ReactivateIdentityCommand(
            identity_id=identity_id,
            reactivated_by=auth.identity_id,
        )
    )
    return MessageResponse(message="Staff member reactivated")
