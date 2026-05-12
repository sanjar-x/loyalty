"""Stub adapter for order creation.

By design, the customer flow uses an explicit ``POST /api/v1/orders`` —
the cart's ``confirm_checkout`` does NOT auto-create an order. This stub
remains in place to satisfy ``IOrderCreationService`` for the existing
cart unit tests and Dishka wiring, but it is NOT invoked in the live
checkout flow.

If the wiring strategy changes (e.g. cart event-driven order creation),
extend ``IOrderCreationService`` with ``identity_id`` and replace this
stub with a real adapter calling Order's
``CreateOrderFromCartHandler``.
"""

import uuid

from src.modules.cart.domain.interfaces import IOrderCreationService
from src.modules.cart.domain.value_objects import CheckoutSnapshot


class OrderCreationStub(IOrderCreationService):
    """Returns a new UUID for each order creation request."""

    async def create_order_from_cart(
        self,
        cart_id: uuid.UUID,
        checkout_id: uuid.UUID,
        snapshot: CheckoutSnapshot,
    ) -> uuid.UUID:
        return uuid.uuid4()
