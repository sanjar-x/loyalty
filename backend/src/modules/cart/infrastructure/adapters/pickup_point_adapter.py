"""Stub adapter for PickupPoint validation.

The Geo module's PickupPoint entity is not yet implemented. This stub
always returns True, allowing the cart checkout flow to proceed.
"""

import uuid

from src.modules.cart.domain.interfaces import IPickupPointReadService


class StubPickupPointAdapter(IPickupPointReadService):
    """Always considers any pickup point as valid."""

    async def exists(self, pickup_point_id: uuid.UUID) -> bool:
        return True
