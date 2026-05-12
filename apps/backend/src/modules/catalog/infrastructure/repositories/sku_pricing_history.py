"""
SKU pricing history repository -- append-only audit writer (ADR-005a).

Implements :class:`IPricingHistoryRepository` (catalog domain port).
One row per real SKU pricing state change; inserts run inside the
caller's UoW so the audit trail stays in lock-step with the SKU
mutation it describes (no audit row, no UPDATE -- and the converse).

The repository is intentionally thin: the table is append-only, the
domain DTO mirrors the column set 1:1, and there are no read paths
in PR-S6 scope. Future analytics/admin queries can extend this class
with retrieval methods without disturbing the apply-path contract.
"""

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.interfaces import (
    IPricingHistoryRepository,
    PricingHistoryEntry,
)
from src.modules.catalog.infrastructure.models import SkuPricingHistoryModel


class SkuPricingHistoryRepository(IPricingHistoryRepository):
    """Append-only repository for the ``sku_pricing_history`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: PricingHistoryEntry) -> None:
        """Persist one audit row.

        The caller's UoW is expected to commit the surrounding
        transaction; this repository never commits or flushes itself.
        """
        await self._session.execute(
            insert(SkuPricingHistoryModel).values(
                sku_id=entry.sku_id,
                previous_status=entry.previous_status,
                new_status=entry.new_status,
                selling_price=entry.selling_price,
                selling_currency=entry.selling_currency,
                formula_version_id=entry.formula_version_id,
                inputs_hash=entry.inputs_hash,
                failure_reason=entry.failure_reason,
                failure_kind=entry.failure_kind,
                correlation_id=entry.correlation_id,
            )
        )
