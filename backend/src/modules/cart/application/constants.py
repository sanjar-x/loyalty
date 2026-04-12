"""
Cart application-layer constants.

Centralizes TTLs and cache key templates.
Domain-level limits (MAX_CART_ITEMS, MAX_QTY_PER_ITEM, CHECKOUT_TTL_MINUTES)
are defined in ``domain.entities`` — import from there.
"""

from src.modules.cart.domain.entities import CHECKOUT_TTL_MINUTES

# Cart TTL (for cleanup jobs — not enforced in MVP)
CART_TTL_AUTH_DAYS = 7
CART_TTL_GUEST_HOURS = 24

__all__ = ["CART_TTL_AUTH_DAYS", "CART_TTL_GUEST_HOURS", "CHECKOUT_TTL_MINUTES"]
