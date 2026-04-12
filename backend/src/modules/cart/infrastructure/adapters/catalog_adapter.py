"""
Catalog ACL adapter — translates SKU data from catalog/supplier ORM models
into cart-domain SkuSnapshot value objects.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.cart.domain.interfaces import ISkuReadService
from src.modules.cart.domain.value_objects import SkuSnapshot
from src.modules.catalog.infrastructure.models import SKU, Product, ProductVariant
from src.modules.supplier.infrastructure.models import Supplier


class CatalogSkuAdapter(ISkuReadService):
    """Reads SKU data from catalog ORM models (infrastructure→infrastructure)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_sku_snapshot(self, sku_id: uuid.UUID) -> SkuSnapshot | None:
        result = await self._get_snapshots([sku_id])
        return result.get(sku_id)

    async def get_sku_snapshots_batch(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, SkuSnapshot]:
        return await self._get_snapshots(sku_ids)

    async def _get_snapshots(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, SkuSnapshot]:
        if not sku_ids:
            return {}

        stmt = (
            select(
                SKU.id,
                SKU.product_id,
                SKU.variant_id,
                SKU.price,
                SKU.currency,
                SKU.is_active,
                SKU.main_image_url,
                Product.title_i18n,
                ProductVariant.name_i18n.label("variant_name_i18n"),
                Supplier.type.label("supplier_type"),
            )
            .join(Product, SKU.product_id == Product.id)
            .join(ProductVariant, SKU.variant_id == ProductVariant.id)
            .join(Supplier, Product.supplier_id == Supplier.id)
            .where(
                SKU.id.in_(sku_ids),
                SKU.deleted_at.is_(None),
            )
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        snapshots: dict[uuid.UUID, SkuSnapshot] = {}
        for row in rows:
            title_i18n = row.title_i18n or {}
            product_name = title_i18n.get("ru") or title_i18n.get("en") or ""
            variant_i18n = row.variant_name_i18n or {}
            variant_label = variant_i18n.get("ru") or variant_i18n.get("en")

            snapshots[row.id] = SkuSnapshot(
                sku_id=row.id,
                product_id=row.product_id,
                variant_id=row.variant_id,
                product_name=product_name,
                variant_label=variant_label,
                image_url=row.main_image_url,
                price_amount=row.price if row.price is not None else 0,
                currency=row.currency or "RUB",
                is_active=row.is_active and row.price is not None,
                supplier_type=row.supplier_type.value if row.supplier_type else "local",
            )

        return snapshots

    async def check_skus_active(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, bool]:
        if not sku_ids:
            return {}
        stmt = select(SKU.id, SKU.is_active).where(
            SKU.id.in_(sku_ids), SKU.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return {row.id: row.is_active for row in result.all()}
