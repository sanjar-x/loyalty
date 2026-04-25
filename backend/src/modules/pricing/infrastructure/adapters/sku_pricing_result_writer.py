"""Anti-corruption writer: pricing result → catalog SKU row (ADR-005).

Whitelisted cross-module ORM access (``pricing → catalog``). Writes the
recompute result directly to the ``skus`` table using a single
optimistic-locked UPDATE. Idempotency is enforced at the SQL level: the
WHERE clause skips writes when the new ``priced_inputs_hash`` already
matches the row's current value (the row is already in the desired
state, so we don't even bump ``version``).

Race safety:

* The recompute service holds a ``SELECT … FOR UPDATE SKIP LOCKED`` on
  the SKU row before invoking the writer; concurrent recompute jobs
  for the same SKU are serialised by the database.
* The UPDATE additionally guards on ``version = :expected_version`` so
  a manual admin edit between SELECT and UPDATE makes the writer return
  ``False`` (no-op) — the recompute service then re-reads and retries.
* ``priced_inputs_hash`` short-circuit makes at-least-once outbox
  delivery exactly-once-effective: a duplicate trigger that observes
  identical inputs lands as a no-op rather than a redundant write.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.infrastructure.models import SKU
from src.modules.geo.infrastructure.models import CurrencyModel
from src.modules.pricing.domain.interfaces import (
    ISkuPricingResultWriter,
    SkuPricingApplyRequest,
    SkuPricingFailureRequest,
)
from src.modules.pricing.infrastructure.models import SkuPricingHistoryModel


class SkuPricingResultWriter(ISkuPricingResultWriter):
    """Writes recompute results into ``skus`` (cross-module adapter)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._fraction_digits_cache: dict[str, int] = {}

    async def apply_success(self, request: SkuPricingApplyRequest) -> bool:
        """Land a fresh selling price.

        Returns ``False`` when nothing changed at the row level (hash
        matched or version moved on). The recompute orchestrator treats
        ``False`` as success — the SKU is already in or past the desired
        state. On a real change, also appends a row to
        ``sku_pricing_history`` so the audit trail stays in lock-step
        with the SKU state (same UoW, same transaction).
        """
        digits = await self._fraction_digits(request.selling_currency)
        amount_minor = int(
            (request.selling_price * Decimal(10) ** digits).to_integral_value()
        )

        stmt = (
            update(SKU)
            .where(
                SKU.id == request.sku_id,
                SKU.version == request.expected_version,
                # SQL-level idempotency: skip when the row already
                # carries this exact provenance hash.
                SKU.priced_inputs_hash.is_distinct_from(request.inputs_hash),
            )
            .values(
                selling_price=amount_minor,
                selling_currency=request.selling_currency,
                pricing_status="priced",
                priced_at=request.priced_at,
                priced_with_formula_version_id=request.formula_version_id,
                priced_inputs_hash=request.inputs_hash,
                priced_failure_reason=None,
                version=SKU.version + 1,
            )
        )
        result = await self._session.execute(stmt)
        applied = (result.rowcount or 0) > 0
        if applied:
            await self._append_history(
                sku_id=request.sku_id,
                previous_status=request.previous_status,
                new_status="priced",
                selling_price=amount_minor,
                selling_currency=request.selling_currency,
                formula_version_id=request.formula_version_id,
                inputs_hash=request.inputs_hash,
                failure_reason=None,
                correlation_id=request.correlation_id,
            )
        return applied

    async def apply_failure(self, request: SkuPricingFailureRequest) -> bool:
        """Land a failure status (clears any stale selling_price).

        Idempotent at the row level: the UPDATE skips when both
        ``pricing_status`` and ``priced_failure_reason`` already match.
        """
        stmt = (
            update(SKU)
            .where(
                SKU.id == request.sku_id,
                SKU.version == request.expected_version,
                # Skip when status + reason already encode this failure.
                # Using OR + IS DISTINCT FROM so a NULL reason on one
                # side doesn't silently equal a non-NULL on the other.
                (
                    SKU.pricing_status.is_distinct_from(request.pricing_status)
                    | SKU.priced_failure_reason.is_distinct_from(request.failure_reason)
                ),
            )
            .values(
                selling_price=None,
                selling_currency=None,
                pricing_status=request.pricing_status,
                priced_at=None,
                priced_with_formula_version_id=None,
                priced_inputs_hash=None,
                priced_failure_reason=request.failure_reason,
                version=SKU.version + 1,
            )
        )
        result = await self._session.execute(stmt)
        applied = (result.rowcount or 0) > 0
        if applied:
            await self._append_history(
                sku_id=request.sku_id,
                previous_status=request.previous_status,
                new_status=request.pricing_status,
                selling_price=None,
                selling_currency=None,
                formula_version_id=None,
                inputs_hash=None,
                failure_reason=request.failure_reason,
                correlation_id=request.correlation_id,
            )
        return applied

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _append_history(
        self,
        *,
        sku_id,
        previous_status: str | None,
        new_status: str,
        selling_price: int | None,
        selling_currency: str | None,
        formula_version_id,
        inputs_hash: str | None,
        failure_reason: str | None,
        correlation_id: str | None,
    ) -> None:
        """Append one row to ``sku_pricing_history``."""
        await self._session.execute(
            insert(SkuPricingHistoryModel).values(
                sku_id=sku_id,
                previous_status=previous_status,
                new_status=new_status,
                selling_price=selling_price,
                selling_currency=selling_currency,
                formula_version_id=formula_version_id,
                inputs_hash=inputs_hash,
                failure_reason=failure_reason,
                correlation_id=correlation_id,
            )
        )

    # ------------------------------------------------------------------
    # Currency precision lookup
    # ------------------------------------------------------------------

    async def _fraction_digits(self, currency_code: str) -> int:
        cached = self._fraction_digits_cache.get(currency_code)
        if cached is not None:
            return cached
        stmt = select(CurrencyModel.minor_unit).where(
            CurrencyModel.code == currency_code
        )
        result = await self._session.execute(stmt)
        digits = result.scalar_one_or_none()
        if digits is None:
            digits = 2
        self._fraction_digits_cache[currency_code] = digits
        return digits
