"""ACL adapter: read a logistics ``DeliveryQuote`` from order's command.

Single anti-corruption bridge between the order module and the
logistics module — same pattern as ``cart→catalog`` ``CatalogSkuAdapter``.
Whitelisted in ``tests/architecture/test_boundaries.py``
(``("order", "logistics")``) so a future addition of another
cross-module ORM touch point fails the boundary fitness test.

Only the priced amount + currency travels across the boundary; the
provider-specific payload (offer_id, tariff_code, weight, …) stays
inside the logistics module — the booking handler will pull it back
through its own quote repository at procurement time.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.logistics.infrastructure.models import DeliveryQuoteModel
from src.modules.order.domain.interfaces import (
    DeliveryQuoteLookupResult,
    IDeliveryQuoteLookup,
)


class DeliveryQuoteAdapter(IDeliveryQuoteLookup):
    """Order-side reader for logistics ``delivery_quotes``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, quote_id: uuid.UUID) -> DeliveryQuoteLookupResult | None:
        stmt = select(
            DeliveryQuoteModel.id,
            DeliveryQuoteModel.total_cost_amount,
            DeliveryQuoteModel.total_cost_currency,
            DeliveryQuoteModel.expires_at,
        ).where(DeliveryQuoteModel.id == quote_id)
        row = (await self._session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return DeliveryQuoteLookupResult(
            quote_id=row.id,
            amount=int(row.total_cost_amount),
            currency=row.total_cost_currency,
            expires_at=row.expires_at,
        )
