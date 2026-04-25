"""Anti-corruption reader: catalog SKU → :class:`SkuPricingInputs` (ADR-005).

Whitelisted cross-module ORM access (``pricing → catalog/supplier``) per
``tests/architecture/test_boundaries.py``. The pricing domain layer
never touches catalog ORM; this adapter materialises a pure DTO.

Stored amounts in catalog are integers in the *smallest* currency unit
(kopecks/fen). Pricing operates in *major* units (Decimal) so the
formula AST stays human-authorable. Conversion uses ISO 4217
minor-unit precision lookups against the geo Currency table.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.infrastructure.models import SKU, Product
from src.modules.geo.infrastructure.models import CurrencyModel
from src.modules.pricing.domain.interfaces import (
    ISkuPricingInputReader,
    SkuPricingInputs,
)
from src.modules.pricing.infrastructure.models import (
    SupplierTypeContextMappingModel,
)
from src.modules.supplier.infrastructure.models import Supplier


def _enum_or_str(value: object) -> str | None:
    """Return ``str(value.value)`` for an Enum, else ``str(value)`` or ``None``.

    SQLAlchemy returns the Python enum member for ``Enum(...)`` columns
    and a plain string for ``String(...)`` columns; the recompute
    pipeline always wants the underlying string.
    """
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


class SkuPricingInputReader(ISkuPricingInputReader):
    """Reads SKU pricing inputs from the catalog ORM (read-only adapter)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        # Cache currency.fraction_digits within a single recompute pass
        # — there are only a handful of currencies and the lookup table
        # rarely changes mid-batch.
        self._fraction_digits_cache: dict[str, int] = {}

    async def read_one(
        self,
        sku_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> SkuPricingInputs | None:
        stmt = (
            select(
                SKU.id,
                SKU.product_id,
                SKU.variant_id,
                SKU.version,
                SKU.purchase_price,
                SKU.purchase_currency,
                SKU.pricing_status,
                Product.primary_category_id,
                Product.supplier_id,
                Supplier.type.label("supplier_type"),
            )
            .join(Product, SKU.product_id == Product.id)
            .outerjoin(Supplier, Product.supplier_id == Supplier.id)
            .where(
                SKU.id == sku_id,
                SKU.deleted_at.is_(None),
            )
        )
        if lock:
            # ``of=SKU`` so we lock only the SKU row even though the
            # SELECT joins Product/Supplier. SKIP LOCKED makes a
            # concurrent recompute task pick a *different* SKU instead
            # of waiting (correctness preserved by inputs_hash).
            stmt = stmt.with_for_update(skip_locked=True, of=SKU)
        result = await self._session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        return await self._row_to_inputs(row)

    async def iter_by_context(
        self,
        context_id: uuid.UUID,
        *,
        batch_size: int = 100,
    ) -> AsyncIterator[list[SkuPricingInputs]]:
        # ADR-005 — fan-out walks the supplier_type → context mapping
        # to project ``context_id`` back onto the set of supplier_types
        # that resolve to it, then yields only SKUs whose supplier sits
        # in that set. Without this filter every ``FormulaPublishedEvent``
        # would enqueue *all* catalog SKUs and 99% would land as no-ops
        # (different context) — wasted queue volume and contention.
        mapping_stmt = select(SupplierTypeContextMappingModel.supplier_type).where(
            SupplierTypeContextMappingModel.context_id == context_id
        )
        result = await self._session.execute(mapping_stmt)
        supplier_types = [row[0] for row in result.all()]
        if not supplier_types:
            # Context not wired to any supplier_type — nothing to do.
            return
        async for batch in self._iter_filtered(
            batch_size=batch_size,
            extra_clauses=(Supplier.type.in_(supplier_types),),
        ):
            yield batch

    async def iter_by_category(
        self,
        category_id: uuid.UUID,
        *,
        batch_size: int = 100,
    ) -> AsyncIterator[list[SkuPricingInputs]]:
        async for batch in self._iter_filtered(
            batch_size=batch_size,
            extra_clauses=(Product.primary_category_id == category_id,),
        ):
            yield batch

    async def iter_by_supplier(
        self,
        supplier_id: uuid.UUID,
        *,
        batch_size: int = 100,
    ) -> AsyncIterator[list[SkuPricingInputs]]:
        async for batch in self._iter_filtered(
            batch_size=batch_size,
            extra_clauses=(Product.supplier_id == supplier_id,),
        ):
            yield batch

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _iter_all(
        self, *, batch_size: int
    ) -> AsyncIterator[list[SkuPricingInputs]]:
        async for batch in self._iter_filtered(batch_size=batch_size, extra_clauses=()):
            yield batch

    async def _iter_filtered(
        self,
        *,
        batch_size: int,
        extra_clauses: tuple,
    ) -> AsyncIterator[list[SkuPricingInputs]]:
        """Page through SKUs ordered by id (UUIDv7 → time-sortable).

        Keyset pagination by ``SKU.id`` keeps memory bounded and avoids
        offset-shift issues if a concurrent insert lands mid-iteration.
        """
        last_id: uuid.UUID | None = None
        while True:
            clauses = [SKU.deleted_at.is_(None), *extra_clauses]
            if last_id is not None:
                clauses.append(SKU.id > last_id)
            stmt = (
                select(
                    SKU.id,
                    SKU.product_id,
                    SKU.variant_id,
                    SKU.version,
                    SKU.purchase_price,
                    SKU.purchase_currency,
                    SKU.pricing_status,
                    Product.primary_category_id,
                    Product.supplier_id,
                    Supplier.type.label("supplier_type"),
                )
                .join(Product, SKU.product_id == Product.id)
                .outerjoin(Supplier, Product.supplier_id == Supplier.id)
                .where(*clauses)
                .order_by(SKU.id.asc())
                .limit(batch_size)
            )
            result = await self._session.execute(stmt)
            rows = list(result.all())
            if not rows:
                return
            chunk: list[SkuPricingInputs] = []
            for row in rows:
                chunk.append(await self._row_to_inputs(row))
            yield chunk
            last_id = rows[-1].id

    async def _row_to_inputs(self, row) -> SkuPricingInputs:
        purchase_price: Decimal | None = None
        # ``purchase_currency`` is mapped via String(3) but a future
        # tightening to Enum(PurchaseCurrency) would yield enum members
        # — normalise both shapes here so downstream literal comparisons
        # in ``recompute._resolve_variable_values`` keep working.
        currency_code: str | None = _enum_or_str(row.purchase_currency)
        if row.purchase_price is not None and currency_code:
            digits = await self._fraction_digits(currency_code)
            purchase_price = (
                Decimal(int(row.purchase_price)) / Decimal(10) ** digits
            ).quantize(Decimal(1) / Decimal(10) ** digits)

        supplier_type_value: str | None = _enum_or_str(row.supplier_type)
        pricing_status_value: str = _enum_or_str(row.pricing_status) or "legacy"

        return SkuPricingInputs(
            sku_id=row.id,
            product_id=row.product_id,
            variant_id=row.variant_id,
            category_id=row.primary_category_id,
            supplier_id=row.supplier_id,
            supplier_type=supplier_type_value,
            purchase_price=purchase_price,
            purchase_currency=currency_code,
            version=row.version,
            pricing_status=pricing_status_value,
        )

    async def _fraction_digits(self, currency_code: str) -> int:
        cached = self._fraction_digits_cache.get(currency_code)
        if cached is not None:
            return cached
        stmt = select(CurrencyModel.minor_unit).where(
            CurrencyModel.code == currency_code
        )
        result = await self._session.execute(stmt)
        digits = result.scalar_one_or_none()
        # ISO 4217 ``minor_unit`` is nullable for currencies without
        # decimal subdivision (XAU, XXX, …); fall back to 2 — the
        # dominant default for fiat — so we never block recompute on
        # a missing entry. The FK on ``skus.purchase_currency`` already
        # prevents an unknown code from reaching here.
        if digits is None:
            digits = 2
        self._fraction_digits_cache[currency_code] = digits
        return digits
