"""Shared cart owner resolution logic for command handlers."""

import uuid

from src.modules.cart.domain.entities import Cart
from src.modules.cart.domain.exceptions import CartNotFoundError
from src.modules.cart.domain.interfaces import ICartRepository


async def find_active_cart_by_owner(
    cart_repo: ICartRepository,
    *,
    identity_id: uuid.UUID | None,
    anonymous_token: str | None,
) -> Cart:
    """Resolve an active cart by identity or anonymous token.

    Raises:
        ValueError: Neither identity_id nor anonymous_token provided.
        CartNotFoundError: No active cart found for the owner.
    """
    if identity_id is not None:
        cart = await cart_repo.get_active_by_identity(identity_id)
    elif anonymous_token is not None:
        cart = await cart_repo.get_active_by_anonymous(anonymous_token)
    else:
        msg = "Either identity_id or anonymous_token is required"
        raise ValueError(msg)
    if cart is None:
        raise CartNotFoundError()
    return cart
