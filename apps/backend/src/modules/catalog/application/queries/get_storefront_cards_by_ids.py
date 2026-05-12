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

from sqlalchemy import case, exists, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.list_storefront_products import (
    ListStorefrontProductsHandler,
)
from src.modules.catalog.application.queries.read_models import (
    StorefrontImageReadModel,
    StorefrontProductCardReadModel,
    StorefrontVariantOptionReadModel,
    StorefrontVariantOptionValueReadModel,
)
from src.modules.catalog.domain.value_objects import MediaRole, ProductStatus
from src.modules.catalog.infrastructure.models import SKU as OrmSKU
from src.modules.catalog.infrastructure.models import Attribute as OrmAttribute
from src.modules.catalog.infrastructure.models import (
    AttributeValue as OrmAttributeValue,
)
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.modules.catalog.infrastructure.models import MediaAsset as OrmMediaAsset
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.modules.catalog.infrastructure.models import ProductVariant as OrmVariant
from src.modules.catalog.infrastructure.models import (
    SKUAttributeValueLink as OrmSKUAttrLink,
)
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier
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

        # ADR-005 — same priceability shape as PLP/search: ``selling_price``
        # wins for ``priced`` SKUs; failure-status SKUs are excluded so
        # the related-products carousel never disagrees with the PDP.
        effective_price_expr = case(
            (OrmSKU.pricing_status == "priced", OrmSKU.selling_price),
            else_=func.coalesce(OrmSKU.price, OrmVariant.default_price),
        )
        priceable_status_clause = OrmSKU.pricing_status.in_(
            ("legacy", "priced", "pending")
        )
        cheapest_sku = (
            select(
                effective_price_expr.label("effective_price"),
                OrmSKU.compare_at_price.label("compare_at_price"),
                func.coalesce(OrmSKU.selling_currency, OrmSKU.currency).label(
                    "sku_currency"
                ),
            )
            .join(OrmVariant, OrmVariant.id == OrmSKU.variant_id)
            .where(
                OrmSKU.product_id == OrmProduct.id,
                OrmSKU.is_active.is_(True),
                OrmSKU.deleted_at.is_(None),
                OrmVariant.deleted_at.is_(None),
                priceable_status_clause,
                effective_price_expr.is_not(None),
            )
            .order_by(effective_price_expr.asc())
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
                priceable_status_clause,
                effective_price_expr.is_not(None),
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
                OrmSupplier.type.label("supplier_type"),
                primary_image.c.image_url,
                primary_image.c.image_variants,
            )
            .join(OrmBrand, OrmBrand.id == OrmProduct.brand_id)
            .outerjoin(OrmSupplier, OrmSupplier.id == OrmProduct.supplier_id)
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

        # Batch-load top-N media assets per product via window function.
        # Without ``ROW_NUMBER`` cap the carousel could return 30+ images
        # × N cards (rich product galleries). 4 covers thumbnail + a few
        # hover-state shots; client-side carousel hits PDP for the rest.
        _MEDIA_PER_CARD = 4
        images_by_product: dict[uuid.UUID, list[StorefrontImageReadModel]] = {}
        matched_ids = list(by_id.keys())
        if matched_ids:
            row_number = (
                func.row_number()
                .over(
                    partition_by=OrmMediaAsset.product_id,
                    order_by=(
                        OrmMediaAsset.variant_id.is_not(None).asc(),
                        (OrmMediaAsset.role != MediaRole.MAIN).asc(),
                        OrmMediaAsset.sort_order.asc(),
                        OrmMediaAsset.created_at.asc(),
                    ),
                )
                .label("rn")
            )
            ranked_sub = (
                select(
                    OrmMediaAsset.product_id,
                    OrmMediaAsset.url,
                    OrmMediaAsset.image_variants,
                    row_number,
                )
                .where(
                    OrmMediaAsset.product_id.in_(matched_ids),
                    OrmMediaAsset.url.is_not(None),
                )
                .subquery()
            )
            media_stmt = (
                select(
                    ranked_sub.c.product_id,
                    ranked_sub.c.url,
                    ranked_sub.c.image_variants,
                )
                .where(ranked_sub.c.rn <= _MEDIA_PER_CARD)
                .order_by(ranked_sub.c.product_id, ranked_sub.c.rn)
            )
            media_rows = await self._session.execute(media_stmt)
            for product_id, url, image_variants in media_rows.all():
                images_by_product.setdefault(product_id, []).append(
                    StorefrontImageReadModel(url=url, image_variants=image_variants)
                )

        variant_options_by_product = await self._load_variant_options(matched_ids)

        cards: list[StorefrontProductCardReadModel] = []
        for pid in ordered:
            row = by_id.get(pid)
            if row is None:
                continue
            card = _row_to_card(row)
            card.images = images_by_product.get(pid, [])
            card.variant_options = variant_options_by_product.get(pid, [])
            cards.append(card)
        return cards

    async def _load_variant_options(
        self, product_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[StorefrontVariantOptionReadModel]]:
        """Aggregate distinct variant attribute options across active priceable SKUs.

        Mirrors the PDP ``variant_options`` aggregation but in a single
        batched SQL pass for many products at once. Drives the size /
        colour pickers on storefront listing cards (trending, for-you,
        similar, also-viewed).
        """
        if not product_ids:
            return {}

        priceable_status_clause = OrmSKU.pricing_status.in_(
            ("legacy", "priced", "pending")
        )
        stmt = (
            select(
                OrmSKU.product_id.label("product_id"),
                OrmAttribute.id.label("attribute_id"),
                OrmAttribute.code.label("attribute_code"),
                OrmAttribute.name_i18n.label("attribute_name_i18n"),
                OrmAttributeValue.id.label("value_id"),
                OrmAttributeValue.code.label("value_code"),
                OrmAttributeValue.value_i18n.label("value_i18n"),
                OrmAttributeValue.meta_data.label("meta_data"),
                OrmAttributeValue.sort_order.label("value_sort_order"),
            )
            .select_from(OrmSKUAttrLink)
            .join(OrmSKU, OrmSKU.id == OrmSKUAttrLink.sku_id)
            .join(OrmVariant, OrmVariant.id == OrmSKU.variant_id)
            .join(OrmAttribute, OrmAttribute.id == OrmSKUAttrLink.attribute_id)
            .join(
                OrmAttributeValue,
                OrmAttributeValue.id == OrmSKUAttrLink.attribute_value_id,
            )
            .where(
                OrmSKU.product_id.in_(product_ids),
                OrmSKU.is_active.is_(True),
                OrmSKU.deleted_at.is_(None),
                OrmVariant.deleted_at.is_(None),
                priceable_status_clause,
                OrmAttributeValue.is_active.is_(True),
            )
            .distinct()
        )

        result = await self._session.execute(stmt)

        # product_id -> attribute_id -> bucket
        index: dict[uuid.UUID, dict[uuid.UUID, dict]] = {}
        for row in result.all():
            per_product = index.setdefault(row.product_id, {})
            bucket = per_product.setdefault(
                row.attribute_id,
                {
                    "attribute_id": row.attribute_id,
                    "attribute_code": row.attribute_code,
                    "attribute_name_i18n": row.attribute_name_i18n or {},
                    "values": {},
                },
            )
            if row.value_id not in bucket["values"]:
                bucket["values"][row.value_id] = StorefrontVariantOptionValueReadModel(
                    value_id=row.value_id,
                    value_code=row.value_code,
                    value_i18n=row.value_i18n or {},
                    meta_data=row.meta_data or {},
                    sort_order=row.value_sort_order or 0,
                )

        out: dict[uuid.UUID, list[StorefrontVariantOptionReadModel]] = {}
        for pid, attr_buckets in index.items():
            options = [
                StorefrontVariantOptionReadModel(
                    attribute_id=bucket["attribute_id"],
                    attribute_code=bucket["attribute_code"],
                    attribute_name_i18n=bucket["attribute_name_i18n"],
                    sort_order=0,
                    values=sorted(
                        bucket["values"].values(),
                        key=lambda v: (v.sort_order, v.value_code),
                    ),
                )
                for bucket in sorted(
                    attr_buckets.values(),
                    key=lambda b: b["attribute_code"],
                )
            ]
            out[pid] = options
        return out


def _row_to_card(row) -> StorefrontProductCardReadModel:
    # Reuse the PLP handler's mapping verbatim to keep output shape aligned.
    return ListStorefrontProductsHandler._row_to_card(row)


# Keep the public handler referenced in __init__ lookups predictable.
__all__ = [
    "GetStorefrontProductCardsByIdsHandler",
    "GetStorefrontProductCardsByIdsQuery",
]
