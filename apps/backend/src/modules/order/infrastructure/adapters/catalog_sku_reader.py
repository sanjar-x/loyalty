"""ACL adapter: order → catalog.

The only file in the order module allowed to import catalog ORM —
whitelisted in ``tests/architecture/test_boundaries.py`` as
``("order","catalog")``. Used by :class:`AdminCreateWalkInOrderHandler`
to snapshot SKU prices + parent product/variant/supplier metadata in
one round-trip when an admin builds a walk-in order outside the cart
pipeline.

Reads ``skus``, ``products``, ``product_variants`` and ``suppliers``
directly (CQRS read-side); never mutates any of them.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.infrastructure.models import (
    SKU,
    Product,
    ProductVariant,
)
from src.modules.order.application.ports import (
    CatalogSkuSnapshot,
    ICatalogSkuPriceReader,
)
from src.modules.supplier.infrastructure.models import Supplier

_DEFAULT_LOCALE_FALLBACKS: tuple[str, ...] = ("ru", "en")


def _pick_localized(i18n: dict | None, locale: str) -> str:
    """Pull a single string out of an i18n dict (e.g. ``title_i18n``).

    Tries the requested locale, then the two-letter standard fallbacks.
    Returns ``""`` when no usable string is found — callers decide
    whether to surface that as a 422 or render a placeholder.
    """
    if not i18n:
        return ""
    if i18n.get(locale):
        return str(i18n[locale])
    for fb in _DEFAULT_LOCALE_FALLBACKS:
        if i18n.get(fb):
            return str(i18n[fb])
    for value in i18n.values():
        if value:
            return str(value)
    return ""


class CatalogSkuPriceReader(ICatalogSkuPriceReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_many(
        self, sku_ids: Sequence[uuid.UUID], *, locale: str = "ru"
    ) -> dict[uuid.UUID, CatalogSkuSnapshot]:
        if not sku_ids:
            return {}
        stmt = (
            select(
                SKU.id,
                SKU.product_id,
                SKU.variant_id,
                SKU.is_active,
                SKU.selling_price,
                SKU.price,
                SKU.currency,
                Product.title_i18n,
                Product.supplier_id,
                ProductVariant.name_i18n,
                Supplier.type.label("supplier_type"),
            )
            .join(Product, Product.id == SKU.product_id)
            .join(ProductVariant, ProductVariant.id == SKU.variant_id)
            .outerjoin(Supplier, Supplier.id == Product.supplier_id)
            .where(SKU.id.in_(list(sku_ids)))
        )
        rows = (await self._session.execute(stmt)).all()
        out: dict[uuid.UUID, CatalogSkuSnapshot] = {}
        for row in rows:
            (
                sku_id,
                product_id,
                variant_id,
                is_active,
                selling_price,
                base_price,
                currency,
                title_i18n,
                _supplier_id,
                variant_name_i18n,
                supplier_type,
            ) = row
            # ADR-005 — selling_price is the customer-facing number;
            # fall back to legacy ``price`` only when recompute has not
            # yet run (status='legacy'). Either ``None`` means the
            # handler will refuse the line.
            effective_price = selling_price if selling_price is not None else base_price
            out[sku_id] = CatalogSkuSnapshot(
                sku_id=sku_id,
                product_id=product_id,
                variant_id=variant_id,
                product_name=_pick_localized(title_i18n, locale),
                variant_label=_pick_localized(variant_name_i18n, locale) or None,
                # ``LOCAL`` is the safe fallback when a product is not
                # linked to a supplier yet — walk-in orders on legacy
                # data should still be creatable but stay on the
                # domestic logistics path.
                supplier_type=(
                    supplier_type.value if supplier_type is not None else "local"
                ),
                selling_price_amount=effective_price,
                currency=currency,
                is_active=bool(is_active),
            )
        return out
