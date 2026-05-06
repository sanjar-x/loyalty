"""Read port over the order bounded context.

Activation flow needs to know whether an order is the customer's first
delivered order (qualifying) and whether it has been refunded since
delivery. This port encapsulates those queries so the referral domain
never reads order ORM directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

import attrs


@attrs.frozen
class OrderSnapshot:
    """Read-only projection of an Order at delivery / refund time."""

    order_id: uuid.UUID
    customer_id: uuid.UUID
    total_amount_kopecks: int
    currency: str
    delivered_at: datetime | None
    is_refunded: bool


class IOrderDirectory(Protocol):
    async def get(self, order_id: uuid.UUID) -> OrderSnapshot | None: ...

    async def is_first_delivered(
        self, *, customer_id: uuid.UUID, order_id: uuid.UUID
    ) -> bool: ...

    async def is_refunded(self, order_id: uuid.UUID) -> bool: ...
