"""Write-only repository for walk-in price-override audit rows."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.order.application.ports import (
    IPriceOverrideAuditWriter,
    PriceOverrideAuditEntry,
)
from src.modules.order.infrastructure.models import OrderLinePriceOverrideModel


class PriceOverrideAuditRepository(IPriceOverrideAuditWriter):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def write_many(self, entries: Sequence[PriceOverrideAuditEntry]) -> None:
        if not entries:
            return
        rows = [
            OrderLinePriceOverrideModel(
                order_id=e.order_id,
                order_item_id=e.order_item_id,
                sku_id=e.sku_id,
                base_price_amount=e.base_price_amount,
                override_price_amount=e.override_price_amount,
                delta_amount=e.override_price_amount - e.base_price_amount,
                currency=e.currency,
                admin_id=e.admin_id,
                reason=e.reason,
            )
            for e in entries
        ]
        self._session.add_all(rows)
        await self._session.flush()
