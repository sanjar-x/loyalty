"""Stub adapter for order creation.

The Order module is not yet implemented. This stub returns a new UUID,
simulating successful order creation so the checkout confirm flow works
end-to-end.
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
