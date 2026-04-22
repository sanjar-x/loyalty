"""
Query handler: fetch storefront product cards for an explicit list of IDs.

Intended for use cases where the ordering is externally determined — e.g.
trending ranking from Redis sorted sets or recommendation endpoints that
merge multiple signals.  The handler preserves the input order and
silently filters out products that are not published / visible.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import exists, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.list_storefront_products import (
    ListStorefrontProductsHandler,
)
from src.modules.catalog.application.queries.read_models import (
    StorefrontProductCardReadModel,
)
from src.modules.catalog.domain.value_objects import MediaRole, ProductStatus
from src.modules.catalog.infrastructure.models import SKU as OrmSKU
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.modules.catalog.infrastructure.models import MediaAsset as OrmMediaAsset
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.modules.catalog.infrastructure.models import ProductVariant as OrmVariant
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class GetStorefrontProductCardsByIdsQuery:
    """Parameters for ``GetStorefrontProductCardsByIdsHandler``.

    ``product_ids`` determines output order — duplicates and unknown IDs
    are dropped.
    """

    product_ids: list[uuid.UUID]


class GetStorefrontProductCardsByIdsHandler:
    """Load storefront cards for a pre-ranked list of product IDs."""

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(handler="GetStorefrontProductCardsByIdsHandler")

    async def handle(
        self, query: GetStorefrontProductCardsByIdsQuery
    ) -> list[StorefrontProductCardReadModel]:
        # Deduplicate while preserving first-seen order.
        seen: set[uuid.UUID] = set()
        ordered: list[uuid.UUID] = []
        for pid in query.product_ids:
            if pid in seen:
                continue
            seen.add(pid)
            ordered.append(pid)

        if not ordered:
            return []

        # Lateral: primary image — identical rules to PLP handler.
        primary_image = (
            select(
                OrmMediaAsset.url.label("image_url"),
                OrmMediaAsset.image_variants.label("image_variants"),
            )
            .where(
                OrmMediaAsset.product_id == OrmProduct.id,
                OrmMediaAsset.url.is_not(None),
            )
            .order_by(
                OrmMediaAsset.variant_id.is_not(None).asc(),
                (OrmMediaAsset.role != MediaRole.MAIN).asc(),
                OrmMediaAsset.sort_order.asc(),
                OrmMediaAsset.created_at.asc(),
            )
            .limit(1)
            .correlate(OrmProduct)
            .lateral("primary_image")
        )

        cheapest_sku = (
            select(
                func.coalesce(OrmSKU.price, OrmVariant.default_price).label(
                    "effective_price"
                ),
                OrmSKU.compare_at_price.label("compare_at_price"),
                OrmSKU.currency.label("sku_currency"),
            )
            .join(OrmVariant, OrmVariant.id == OrmSKU.variant_id)
            .where(
                OrmSKU.product_id == OrmProduct.id,
                OrmSKU.is_active.is_(True),
                OrmSKU.deleted_at.is_(None),
                OrmVariant.deleted_at.is_(None),
                func.coalesce(OrmSKU.price, OrmVariant.default_price).is_not(None),
            )
            .order_by(func.coalesce(OrmSKU.price, OrmVariant.default_price).asc())
            .limit(1)
            .correlate(OrmProduct)
            .lateral("cheapest_sku")
        )

        variant_count_sub = (
            select(func.count(OrmVariant.id))
            .where(
                OrmVariant.product_id == OrmProduct.id,
                OrmVariant.deleted_at.is_(None),
            )
            .correlate(OrmProduct)
            .scalar_subquery()
        )

        has_stock_sub = exists(
            select(literal(1))
            .select_from(OrmSKU)
            .join(OrmVariant, OrmVariant.id == OrmSKU.variant_id)
            .where(
                OrmSKU.product_id == OrmProduct.id,
                OrmSKU.is_active.is_(True),
                OrmSKU.deleted_at.is_(None),
                OrmVariant.deleted_at.is_(None),
                func.coalesce(OrmSKU.price, OrmVariant.default_price).is_not(None),
            )
        ).correlate(OrmProduct)

        stmt = (
            select(
                OrmProduct.id.label("product_id"),
                OrmProduct.slug,
                OrmProduct.title_i18n,
                OrmProduct.brand_id,
                OrmProduct.popularity_score,
                OrmProduct.published_at,
                cheapest_sku.c.effective_price,
                cheapest_sku.c.compare_at_price,
                cheapest_sku.c.sku_currency,
                variant_count_sub.label("variant_count"),
                has_stock_sub.label("has_stock"),
                OrmBrand.name.label("brand_name"),
                OrmBrand.slug.label("brand_slug"),
                OrmBrand.logo_url.label("brand_logo_url"),
                primary_image.c.image_url,
                primary_image.c.image_variants,
            )
            .join(OrmBrand, OrmBrand.id == OrmProduct.brand_id)
            .outerjoin(cheapest_sku, literal(True))
            .outerjoin(primary_image, literal(True))
            .where(
                OrmProduct.id.in_(ordered),
                OrmProduct.status == ProductStatus.PUBLISHED,
                OrmProduct.is_visible.is_(True),
                OrmProduct.deleted_at.is_(None),
            )
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        by_id = {row.product_id: row for row in rows}
        cards: list[StorefrontProductCardReadModel] = []
        for pid in ordered:
            row = by_id.get(pid)
            if row is None:
                continue
            cards.append(_row_to_card(row))
        return cards


def _row_to_card(row) -> StorefrontProductCardReadModel:
    # Reuse the PLP handler's mapping verbatim to keep output shape aligned.
    return ListStorefrontProductsHandler._row_to_card(row)


# Keep the public handler referenced in __init__ lookups predictable.
__all__ = [
    "GetStorefrontProductCardsByIdsHandler",
    "GetStorefrontProductCardsByIdsQuery",
]
