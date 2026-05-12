"""Pricing-backed implementation of :class:`ISkuWeightResolver`.

Resolves the ``weight_g`` parcel weight that the storefront feeds into
``CalculateRatesHandler``. The marketplace dropships from China — the
real per-unit weight is unknown until parcels arrive at the RF
warehouse, so during checkout we fall back to a category-level estimate
maintained by ops in the pricing module:

1. Look up each SKU's ``Product.primary_category_id`` in catalog.
2. Read ``CategoryPricingSettings.values["weight_g"]`` for that
   ``(category_id, active_context_id)`` in pricing.
3. If no override exists, fall back to
   ``Variable[code="weight_g"].default_value`` (system default, 500 g).

The active pricing context is resolved per-SKU from the supplier type
via ``SupplierTypeContextMappingModel`` — same mechanism the SKU
recompute pipeline uses (ADR-005). This keeps logistics weight aligned
with the very same context whose formula priced the SKU.

Cross-module ORM access (``logistics → catalog`` + ``logistics → pricing``
+ ``logistics → supplier``) is whitelisted in
``tests/architecture/test_boundaries.py`` for this module path only.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.infrastructure.models import SKU, Product
from src.modules.logistics.domain.interfaces import ISkuWeightResolver
from src.modules.pricing.infrastructure.models import (
    CategoryPricingSettingsModel,
    SupplierTypeContextMappingModel,
    VariableModel,
)
from src.modules.supplier.infrastructure.models import Supplier
from src.shared.interfaces.logger import ILogger

# Variable code shared with ``seed/pricing/system_variables.json``. Kept as
# a constant so a typo here vs. there fails a single grep, not a quote.
WEIGHT_VARIABLE_CODE = "weight_g"

# Hard floor in case the seed has been tampered with and no default
# survived in the variables registry. Matches the seed's default_value.
_FALLBACK_DEFAULT_GRAMS = 500


class PricingWeightAdapter(ISkuWeightResolver):
    """Reads category weight from pricing, joining SKU → Product → Supplier.

    Stateful within a request: the per-instance cache for the global
    fallback / context lookup avoids hitting ``pricing_variables`` and
    ``pricing_supplier_type_context_mapping`` once per SKU in a batch.
    """

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(adapter="PricingWeightAdapter")
        self._default_grams: int | None = None
        self._supplier_type_context_cache: dict[str, uuid.UUID] = {}

    async def resolve_weight_grams(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not sku_ids:
            return {}

        # 1. Batch SKU → (category_id, supplier_type)
        sku_rows = await self._fetch_sku_routing(sku_ids)
        if not sku_rows:
            return {}

        # 2. Resolve unique supplier_types → context_ids in one pass.
        unique_supplier_types = {
            row.supplier_type for row in sku_rows if row.supplier_type is not None
        }
        await self._warm_supplier_type_contexts(unique_supplier_types)

        # 3. Build the (category_id, context_id) lookup set and fetch settings.
        wanted_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()
        for row in sku_rows:
            ctx = self._supplier_type_context_cache.get(row.supplier_type or "")
            if ctx is None or row.category_id is None:
                continue
            wanted_pairs.add((row.category_id, ctx))

        category_weights = await self._fetch_category_weights(wanted_pairs)

        # 4. Pull global default (variable.default_value) once.
        default_grams = await self._resolve_default_grams()

        # 5. Compose result map.
        result: dict[uuid.UUID, int] = {}
        for row in sku_rows:
            grams = self._resolve_one(
                category_id=row.category_id,
                supplier_type=row.supplier_type,
                category_weights=category_weights,
                default_grams=default_grams,
            )
            result[row.sku_id] = grams
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_sku_routing(self, sku_ids: list[uuid.UUID]) -> list[_SkuRow]:
        stmt = (
            select(
                SKU.id.label("sku_id"),
                Product.primary_category_id.label("category_id"),
                Supplier.type.label("supplier_type"),
            )
            .join(Product, SKU.product_id == Product.id)
            .outerjoin(Supplier, Product.supplier_id == Supplier.id)
            .where(SKU.id.in_(sku_ids))
        )
        result = await self._session.execute(stmt)
        rows: list[_SkuRow] = []
        for raw in result.all():
            rows.append(
                _SkuRow(
                    sku_id=raw.sku_id,
                    category_id=raw.category_id,
                    supplier_type=_enum_or_str(raw.supplier_type),
                )
            )
        return rows

    async def _warm_supplier_type_contexts(self, supplier_types: Iterable[str]) -> None:
        missing = [
            st
            for st in supplier_types
            if st and st not in self._supplier_type_context_cache
        ]
        if not missing:
            return
        stmt = select(
            SupplierTypeContextMappingModel.supplier_type,
            SupplierTypeContextMappingModel.context_id,
        ).where(SupplierTypeContextMappingModel.supplier_type.in_(missing))
        result = await self._session.execute(stmt)
        for row in result.all():
            self._supplier_type_context_cache[row.supplier_type] = row.context_id

    async def _fetch_category_weights(
        self, pairs: set[tuple[uuid.UUID, uuid.UUID]]
    ) -> dict[tuple[uuid.UUID, uuid.UUID], int]:
        if not pairs:
            return {}
        category_ids = {cat_id for cat_id, _ in pairs}
        context_ids = {ctx_id for _, ctx_id in pairs}
        stmt = select(
            CategoryPricingSettingsModel.category_id,
            CategoryPricingSettingsModel.context_id,
            CategoryPricingSettingsModel.values,
        ).where(
            CategoryPricingSettingsModel.category_id.in_(category_ids),
            CategoryPricingSettingsModel.context_id.in_(context_ids),
        )
        result = await self._session.execute(stmt)
        weights: dict[tuple[uuid.UUID, uuid.UUID], int] = {}
        for row in result.all():
            key = (row.category_id, row.context_id)
            if key not in pairs:
                # Cross-product over IN clauses can return rows we never
                # asked for; keep only the (category, context) we actually
                # need so the per-SKU lookup stays exact.
                continue
            grams = _coerce_grams(row.values.get(WEIGHT_VARIABLE_CODE))
            if grams is not None:
                weights[key] = grams
        return weights

    async def _resolve_default_grams(self) -> int:
        if self._default_grams is not None:
            return self._default_grams
        stmt = select(VariableModel.default_value).where(
            VariableModel.code == WEIGHT_VARIABLE_CODE
        )
        result = await self._session.execute(stmt)
        raw = result.scalar_one_or_none()
        grams = _coerce_grams(raw)
        if grams is None:
            self._logger.warning(
                "weight_g variable missing default — using hardcoded fallback",
                fallback_grams=_FALLBACK_DEFAULT_GRAMS,
            )
            grams = _FALLBACK_DEFAULT_GRAMS
        self._default_grams = grams
        return grams

    def _resolve_one(
        self,
        *,
        category_id: uuid.UUID | None,
        supplier_type: str | None,
        category_weights: dict[tuple[uuid.UUID, uuid.UUID], int],
        default_grams: int,
    ) -> int:
        if category_id is None or supplier_type is None:
            return default_grams
        ctx = self._supplier_type_context_cache.get(supplier_type)
        if ctx is None:
            return default_grams
        return category_weights.get((category_id, ctx), default_grams)


# ---------------------------------------------------------------------------
# Module-private helpers
# ---------------------------------------------------------------------------


class _SkuRow:
    """Tiny row holder so the SQL block stays declarative."""

    __slots__ = ("category_id", "sku_id", "supplier_type")

    def __init__(
        self,
        *,
        sku_id: uuid.UUID,
        category_id: uuid.UUID | None,
        supplier_type: str | None,
    ) -> None:
        self.sku_id = sku_id
        self.category_id = category_id
        self.supplier_type = supplier_type


def _enum_or_str(value: object) -> str | None:
    """Normalise SQLAlchemy enum / string columns to a plain str."""
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _coerce_grams(raw: object) -> int | None:
    """Convert a JSONB / Numeric weight value to a positive int (grams).

    ``CategoryPricingSettings.values`` stores Decimals as JSON strings, so
    callers may receive ``"450"``, ``Decimal("450")``, or — for the
    variable default — a plain ``Decimal`` from the Numeric column. A
    non-positive value is treated as missing (logged upstream) so a
    misconfigured row falls back to the system default rather than
    poisoning every quote with weight=0 → CDEK rejecting the package.
    """
    if raw is None:
        return None
    try:
        if isinstance(raw, (Decimal, int, float)):
            grams = int(raw)
        elif isinstance(raw, str):
            grams = int(Decimal(raw))
        else:
            return None
    except InvalidOperation, ValueError, TypeError:
        return None
    if grams <= 0:
        return None
    return grams


__all__ = ["WEIGHT_VARIABLE_CODE", "PricingWeightAdapter"]
