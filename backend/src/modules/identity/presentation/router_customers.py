"""Customer management admin router.

Provides endpoints for listing, viewing, deactivating, and reactivating
customer accounts. Requires ``customers:read`` for listing/viewing and
``customers:manage`` for deactivation/reactivation.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query

from src.modules.identity.application.commands.admin_deactivate_identity import (
    AdminDeactivateIdentityCommand,
    AdminDeactivateIdentityHandler,
)
from src.modules.identity.application.commands.reactivate_identity import (
    ReactivateIdentityCommand,
    ReactivateIdentityHandler,
)
from src.modules.identity.application.queries.get_customer_detail import (
    GetCustomerDetailHandler,
    GetCustomerDetailQuery,
)
from src.modules.identity.application.queries.list_customers import (
    ListCustomersHandler,
    ListCustomersQuery,
)
from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_auth_context,
)
from src.modules.identity.presentation.schemas import (
    AdminDeactivateRequest,
    CustomerDetailResponse,
    CustomerListItemResponse,
    CustomerListResponse,
    MessageResponse,
    RoleInfoResponse,
)
from src.shared.interfaces.auth import AuthContext

customer_admin_router = APIRouter(
    prefix="/admin/customers",
    tags=["Admin — Customer Management"],
    route_class=DishkaRoute,
)


# ---------------------------------------------------------------------------
# Customer listing and detail endpoints
# ---------------------------------------------------------------------------


@customer_admin_router.get(
    "",
    response_model=CustomerListResponse,
    summary="List customers (paginated)",
    dependencies=[Depends(RequirePermission("customers:read"))],
)
async def list_customers(
    handler: FromDishka[ListCustomersHandler],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    is_active: bool | None = Query(None),
    sort_by: str = Query("created_at", pattern=r"^(created_at|email|last_name)$"),
    sort_order: str = Query("desc", pattern=r"^(asc|desc)$"),
) -> CustomerListResponse:
    """List customers with pagination and filtering.

    Args:
        handler: The list-customers query handler.
        offset: Pagination offset.
        limit: Page size (1-100).
        search: Optional ILIKE search on email, first_name, last_name.
        is_active: Optional filter by active status.
        sort_by: Sort column (created_at, email, last_name).
        sort_order: Sort direction (asc, desc).

    Returns:
        Paginated list of customers with role names.
    """
    result = await handler.handle(
        ListCustomersQuery(
            offset=offset,
            limit=limit,
            search=search,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )
    return CustomerListResponse(
        items=[
            CustomerListItemResponse(
                identity_id=item.identity_id,
                email=item.email,
                first_name=item.first_name,
                last_name=item.last_name,
                phone=item.phone,
                referral_code=item.referral_code,
                username=item.username,
                auth_methods=item.auth_methods,
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


@customer_admin_router.get(
    "/{identity_id}",
    response_model=CustomerDetailResponse,
    summary="Get customer detail",
    dependencies=[Depends(RequirePermission("customers:read"))],
)
async def get_customer_detail(
    identity_id: uuid.UUID,
    handler: FromDishka[GetCustomerDetailHandler],
) -> CustomerDetailResponse:
    """Get full detail for a single customer.

    Args:
        identity_id: The customer's identity UUID.
        handler: The get-customer-detail query handler.

    Returns:
        Full customer detail with roles.
    """
    result = await handler.handle(GetCustomerDetailQuery(identity_id=identity_id))
    return CustomerDetailResponse(
        identity_id=result.identity_id,
        email=result.email,
        auth_type=result.auth_type,
        is_active=result.is_active,
        first_name=result.first_name,
        last_name=result.last_name,
        phone=result.phone,
        referral_code=result.referral_code,
        username=result.username,
        auth_methods=result.auth_methods,
        referred_by=result.referred_by,
        roles=[
            RoleInfoResponse(id=r.id, name=r.name, description=r.description, is_system=r.is_system)
            for r in result.roles
        ],
        created_at=result.created_at,
        deactivated_at=result.deactivated_at,
        deactivated_by=result.deactivated_by,
    )


# ---------------------------------------------------------------------------
# Customer deactivation/reactivation endpoints
# ---------------------------------------------------------------------------


@customer_admin_router.post(
    "/{identity_id}/deactivate",
    response_model=MessageResponse,
    summary="Deactivate a customer",
    dependencies=[Depends(RequirePermission("customers:manage"))],
)
async def deactivate_customer(
    identity_id: uuid.UUID,
    body: AdminDeactivateRequest,
    handler: FromDishka[AdminDeactivateIdentityHandler],
    auth: AuthContext = Depends(get_auth_context),
) -> MessageResponse:
    """Deactivate a customer account.

    Args:
        identity_id: The target customer's identity UUID.
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
    return MessageResponse(message="Customer deactivated")


@customer_admin_router.post(
    "/{identity_id}/reactivate",
    response_model=MessageResponse,
    summary="Reactivate a customer",
    dependencies=[Depends(RequirePermission("customers:manage"))],
)
async def reactivate_customer(
    identity_id: uuid.UUID,
    handler: FromDishka[ReactivateIdentityHandler],
    auth: AuthContext = Depends(get_auth_context),
) -> MessageResponse:
    """Reactivate a deactivated customer account.

    Args:
        identity_id: The target customer's identity UUID.
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
    return MessageResponse(message="Customer reactivated")
