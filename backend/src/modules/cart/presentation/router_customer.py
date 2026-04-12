"""
FastAPI router for customer-facing cart endpoints.

Supports both authenticated (identity_id from JWT) and guest
(anonymous_token header) flows.
"""

import uuid
from typing import Annotated, Any

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.modules.cart.application.commands.add_item import (
    AddItemCommand,
    AddItemHandler,
)
from src.modules.cart.application.commands.cancel_checkout import (
    CancelCheckoutCommand,
    CancelCheckoutHandler,
)
from src.modules.cart.application.commands.clear_cart import (
    ClearCartCommand,
    ClearCartHandler,
)
from src.modules.cart.application.commands.confirm_checkout import (
    ConfirmCheckoutCommand,
    ConfirmCheckoutHandler,
)
from src.modules.cart.application.commands.initiate_checkout import (
    InitiateCheckoutCommand,
    InitiateCheckoutHandler,
)
from src.modules.cart.application.commands.merge_carts import (
    MergeCartsCommand,
    MergeCartsHandler,
)
from src.modules.cart.application.commands.remove_item import (
    RemoveItemCommand,
    RemoveItemHandler,
)
from src.modules.cart.application.commands.update_quantity import (
    UpdateQuantityCommand,
    UpdateQuantityHandler,
)
from src.modules.cart.application.queries.get_cart import (
    GetCartHandler,
    GetCartQuery,
)
from src.modules.cart.application.queries.get_cart_summary import (
    GetCartSummaryHandler,
    GetCartSummaryQuery,
)
from src.modules.cart.presentation.schemas import (
    AddItemRequest,
    AddItemResponse,
    AnonymousTokenResponse,
    CartResponse,
    CartSummaryResponse,
    CheckoutConfirmedResponse,
    CheckoutInitiatedResponse,
    ConfirmCheckoutRequest,
    InitiateCheckoutRequest,
    MergeCartRequest,
    MoneyResponse,
    UpdateQuantityRequest,
)
from src.shared.exceptions import UnauthorizedError
from src.shared.interfaces.security import ITokenProvider

_bearer_scheme = HTTPBearer(auto_error=False)

BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
]

cart_router = APIRouter(
    prefix="/cart",
    tags=["Cart"],
    route_class=DishkaRoute,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _resolve_identity(
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
) -> str | None:
    """Extract identity_id from JWT if present; return None for guests."""
    if not credentials:
        return None
    try:
        payload: dict[str, Any] = token_provider.decode_access_token(
            credentials.credentials
        )
        return payload.get("sub")
    except Exception:
        return None


def _require_auth(identity_id: str | None) -> uuid.UUID:
    """Raise if not authenticated."""
    if not identity_id:
        raise UnauthorizedError(
            message="Authentication required.",
            error_code="AUTH_REQUIRED",
        )
    return uuid.UUID(identity_id)


# ---------------------------------------------------------------------------
# Cart CRUD
# ---------------------------------------------------------------------------


@cart_router.post(
    "/items",
    status_code=status.HTTP_201_CREATED,
    response_model=AddItemResponse,
    summary="Add item to cart",
)
async def add_item(
    body: AddItemRequest,
    handler: FromDishka[AddItemHandler],
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
    x_anonymous_token: str | None = Header(None),
) -> AddItemResponse:
    identity_id = await _resolve_identity(credentials, token_provider)
    command = AddItemCommand(
        identity_id=uuid.UUID(identity_id) if identity_id else None,
        anonymous_token=x_anonymous_token,
        sku_id=body.sku_id,
        quantity=body.quantity,
    )
    result = await handler.handle(command)
    return AddItemResponse(cart_id=result.cart_id, item_id=result.item_id)


@cart_router.delete(
    "/items/{sku_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove item from cart",
)
async def remove_item(
    sku_id: uuid.UUID,
    handler: FromDishka[RemoveItemHandler],
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
    x_anonymous_token: str | None = Header(None),
) -> None:
    identity_id = await _resolve_identity(credentials, token_provider)
    command = RemoveItemCommand(
        identity_id=uuid.UUID(identity_id) if identity_id else None,
        anonymous_token=x_anonymous_token,
        sku_id=sku_id,
    )
    await handler.handle(command)


@cart_router.patch(
    "/items/{sku_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update item quantity",
)
async def update_quantity(
    sku_id: uuid.UUID,
    body: UpdateQuantityRequest,
    handler: FromDishka[UpdateQuantityHandler],
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
    x_anonymous_token: str | None = Header(None),
) -> None:
    identity_id = await _resolve_identity(credentials, token_provider)
    command = UpdateQuantityCommand(
        identity_id=uuid.UUID(identity_id) if identity_id else None,
        anonymous_token=x_anonymous_token,
        sku_id=sku_id,
        quantity=body.quantity,
    )
    await handler.handle(command)


@cart_router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear all items from cart",
)
async def clear_cart(
    handler: FromDishka[ClearCartHandler],
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
    x_anonymous_token: str | None = Header(None),
) -> None:
    identity_id = await _resolve_identity(credentials, token_provider)
    command = ClearCartCommand(
        identity_id=uuid.UUID(identity_id) if identity_id else None,
        anonymous_token=x_anonymous_token,
    )
    await handler.handle(command)


# ---------------------------------------------------------------------------
# Cart Read
# ---------------------------------------------------------------------------


@cart_router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=CartResponse,
    summary="Get current cart with live prices",
)
async def get_cart(
    handler: FromDishka[GetCartHandler],
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
    x_anonymous_token: str | None = Header(None),
) -> CartResponse:
    identity_id = await _resolve_identity(credentials, token_provider)
    query = GetCartQuery(
        identity_id=uuid.UUID(identity_id) if identity_id else None,
        anonymous_token=x_anonymous_token,
    )
    result = await handler.handle(query)
    return _map_cart_response(result)


@cart_router.get(
    "/summary",
    status_code=status.HTTP_200_OK,
    response_model=CartSummaryResponse,
    summary="Get cart item count and total",
)
async def get_cart_summary(
    handler: FromDishka[GetCartSummaryHandler],
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
    x_anonymous_token: str | None = Header(None),
) -> CartSummaryResponse:
    identity_id = await _resolve_identity(credentials, token_provider)
    query = GetCartSummaryQuery(
        identity_id=uuid.UUID(identity_id) if identity_id else None,
        anonymous_token=x_anonymous_token,
    )
    result = await handler.handle(query)
    return CartSummaryResponse(
        item_count=result.item_count,
        total=MoneyResponse(amount=result.total_amount, currency=result.currency),
    )


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------


@cart_router.post(
    "/checkout",
    status_code=status.HTTP_200_OK,
    response_model=CheckoutInitiatedResponse,
    summary="Initiate checkout (freeze cart, create snapshot)",
)
async def initiate_checkout(
    body: InitiateCheckoutRequest,
    handler: FromDishka[InitiateCheckoutHandler],
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
) -> CheckoutInitiatedResponse:
    identity_id = _require_auth(await _resolve_identity(credentials, token_provider))
    command = InitiateCheckoutCommand(
        identity_id=identity_id,
        pickup_point_id=body.pickup_point_id,
    )
    result = await handler.handle(command)
    return CheckoutInitiatedResponse(
        attempt_id=result.attempt_id,
        snapshot_id=result.snapshot_id,
        expires_at=result.expires_at,
    )


@cart_router.post(
    "/checkout/confirm",
    status_code=status.HTTP_200_OK,
    response_model=CheckoutConfirmedResponse,
    summary="Confirm checkout (validate prices, create order)",
)
async def confirm_checkout(
    body: ConfirmCheckoutRequest,
    handler: FromDishka[ConfirmCheckoutHandler],
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
) -> CheckoutConfirmedResponse:
    identity_id = _require_auth(await _resolve_identity(credentials, token_provider))
    command = ConfirmCheckoutCommand(
        identity_id=identity_id,
        attempt_id=body.attempt_id,
    )
    result = await handler.handle(command)
    return CheckoutConfirmedResponse(order_id=result.order_id)


@cart_router.post(
    "/checkout/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel checkout (unfreeze cart)",
)
async def cancel_checkout(
    handler: FromDishka[CancelCheckoutHandler],
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
) -> None:
    identity_id = _require_auth(await _resolve_identity(credentials, token_provider))
    command = CancelCheckoutCommand(identity_id=identity_id)
    await handler.handle(command)


# ---------------------------------------------------------------------------
# Merge (post-login)
# ---------------------------------------------------------------------------


@cart_router.post(
    "/merge",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Merge guest cart into authenticated cart",
)
async def merge_carts(
    body: MergeCartRequest,
    handler: FromDishka[MergeCartsHandler],
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
) -> None:
    identity_id = _require_auth(await _resolve_identity(credentials, token_provider))
    command = MergeCartsCommand(
        identity_id=identity_id,
        anonymous_token=body.anonymous_token,
    )
    await handler.handle(command)


# ---------------------------------------------------------------------------
# Anonymous token
# ---------------------------------------------------------------------------


@cart_router.post(
    "/anonymous-token",
    status_code=status.HTTP_201_CREATED,
    response_model=AnonymousTokenResponse,
    summary="Generate anonymous cart token for guests",
)
async def create_anonymous_token() -> AnonymousTokenResponse:
    token = uuid.uuid4().hex
    return AnonymousTokenResponse(token=token)


# ---------------------------------------------------------------------------
# Response mapping helpers
# ---------------------------------------------------------------------------


def _map_cart_response(read_model: Any) -> CartResponse:
    from src.modules.cart.presentation.schemas import (
        CartGroupResponse,
        CartItemResponse,
    )

    groups = []
    for g in read_model.groups:
        items = [
            CartItemResponse(
                id=item.id,
                sku_id=item.sku_id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                product_name=item.product_name,
                variant_label=item.variant_label,
                image_url=item.image_url,
                quantity=item.quantity,
                unit_price=MoneyResponse(
                    amount=item.unit_price_amount, currency=item.currency
                )
                if item.unit_price_amount is not None
                else None,
                line_total=MoneyResponse(
                    amount=item.line_total_amount, currency=item.currency
                )
                if item.line_total_amount is not None
                else None,
                supplier_type=item.supplier_type,
                added_at=item.added_at,
            )
            for item in g.items
        ]
        groups.append(
            CartGroupResponse(
                supplier_type=g.supplier_type,
                items=items,
                subtotal=MoneyResponse(amount=g.subtotal_amount, currency=g.currency),
            )
        )

    return CartResponse(
        id=read_model.id,
        status=read_model.status,
        item_count=read_model.item_count,
        total=MoneyResponse(
            amount=read_model.total_amount, currency=read_model.currency
        ),
        groups=groups,
        frozen_until=read_model.frozen_until,
        created_at=read_model.created_at,
        updated_at=read_model.updated_at,
    )
