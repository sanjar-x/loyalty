"""
Query handler: compute facet counts for storefront product filtering.

Implements the **post_filter** pattern: for each facet group the counts are
computed with every active filter applied *except* the group's own filter.
This gives "what-if" counts that let the frontend show how many products
would match if the user toggles a value.

Only product-level attributes are faceted (variant-level deferred).

CQRS read side — queries ORM directly, returns read models.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass

from sqlalchemy import exists, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.modules.catalog.application.constants import (
    STOREFRONT_FACET_CACHE_TTL,
    storefront_facet_cache_key,
)
from src.modules.catalog.application.queries.read_models import (
    BrandFacetValueReadModel,
    FacetGroupReadModel,
    FacetResultReadModel,
    FacetValueCountReadModel,
    PriceRangeReadModel,
    StorefrontFilterAttributeReadModel,
)
from src.modules.catalog.application.queries.storefront import (
    StorefrontFilterableAttributesHandler,
)
from src.modules.catalog.domain.value_objects import ProductStatus
from src.modules.catalog.infrastructure.models import SKU as OrmSKU
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValue as OrmProductAttributeValue,
)
from src.modules.catalog.infrastructure.models import ProductVariant as OrmVariant
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class ComputeFacetsQuery:
    """Parameters for facet count computation.

    Mirrors ``StorefrontProductListQuery`` filters so that facet counts
    are consistent with the product listing.
    """

    category_id: uuid.UUID
    brand_ids: list[uuid.UUID] | None = None
    price_min: int | None = None
    price_max: int | None = None
    in_stock: bool | None = None
    attribute_filters: dict[str, list[str]] | None = None


class ComputeFacetsHandler:
    """Compute facet counts for the storefront filter panel."""

    def __init__(
        self,
        session: AsyncSession,
        filter_meta_handler: StorefrontFilterableAttributesHandler,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._session = session
        self._filter_meta = filter_meta_handler
        self._cache = cache
        self._logger = logger.bind(handler="ComputeFacetsHandler")

    async def handle(self, query: ComputeFacetsQuery) -> FacetResultReadModel:
        cache_key = storefront_facet_cache_key(self._query_hash(query))
        cached = await self._cache.get(cache_key)
        if cached:
            return FacetResultReadModel.model_validate(json.loads(cached))

        # 1. Get filterable attribute metadata (cached in the filter handler).
        try:
            filter_meta = await self._filter_meta.handle(query.category_id)
        except Exception:
            self._logger.warning(
                "filter_meta_unavailable", category_id=str(query.category_id)
            )
            return FacetResultReadModel()

        # 2. Restrict to product-level filterable attributes.
        attr_by_code: dict[str, StorefrontFilterAttributeReadModel] = {
            a.code: a for a in filter_meta.attributes if a.level == "product"
        }

        # 3. Validate and resolve incoming attribute filters → value IDs.
        resolved_filters: dict[str, list[uuid.UUID]] = {}
        for code, slugs in (query.attribute_filters or {}).items():
            meta = attr_by_code.get(code)
            if meta is None:
                continue
            slug_to_id = {v.slug: v.id for v in meta.values}
            ids = [slug_to_id[s] for s in slugs if s in slug_to_id]
            if ids:
                resolved_filters[code] = ids

        # 4. Attribute facets (post_filter pattern).
        attribute_facets: list[FacetGroupReadModel] = []
        for attr_meta in attr_by_code.values():
            excl = {k: v for k, v in resolved_filters.items() if k != attr_meta.code}
            counts = await self._count_attr_values(
                category_id=query.category_id,
                attribute_id=attr_meta.attribute_id,
                brand_ids=query.brand_ids,
                price_min=query.price_min,
                price_max=query.price_max,
                in_stock=query.in_stock,
                attr_filters=excl,
            )
            facet_values = [
                FacetValueCountReadModel(
                    value_id=v.id,
                    code=v.code,
                    slug=v.slug,
                    value_i18n=v.value_i18n,
                    meta_data=v.meta_data,
                    value_group=v.value_group,
                    sort_order=v.sort_order,
                    count=counts.get(v.id, 0),
                )
                for v in attr_meta.values
            ]
            attribute_facets.append(
                FacetGroupReadModel(
                    attribute_id=attr_meta.attribute_id,
                    code=attr_meta.code,
                    slug=attr_meta.slug,
                    name_i18n=attr_meta.name_i18n,
                    ui_type=attr_meta.ui_type,
                    selection_mode=attr_meta.selection_mode,
                    values=facet_values,
                )
            )

        # 5. Brand facet (post_filter: exclude brand filter).
        brand_facets = await self._count_brands(
            category_id=query.category_id,
            price_min=query.price_min,
            price_max=query.price_max,
            in_stock=query.in_stock,
            attr_filters=resolved_filters,
        )

        # 6. Price range (post_filter: exclude price filter).
        price_range = await self._compute_price_range(
            category_id=query.category_id,
            brand_ids=query.brand_ids,
            in_stock=query.in_stock,
            attr_filters=resolved_filters,
        )

        # 7. Total matching products (all filters applied).
        total = await self._count_total(
            category_id=query.category_id,
            brand_ids=query.brand_ids,
            price_min=query.price_min,
            price_max=query.price_max,
            in_stock=query.in_stock,
            attr_filters=resolved_filters,
        )

        result = FacetResultReadModel(
            attribute_facets=attribute_facets,
            brand_facets=brand_facets,
            price_range=price_range,
            total_products=total,
        )
        await self._cache_result(cache_key, result)
        return result

    # ------------------------------------------------------------------
    # Base eligibility conditions
    # ------------------------------------------------------------------

    @staticmethod
    def _base_where():
        """Canonical product eligibility conditions."""
        return [
            OrmProduct.status == ProductStatus.PUBLISHED,
            OrmProduct.is_visible.is_(True),
            OrmProduct.deleted_at.is_(None),
        ]

    @staticmethod
    def _min_price_subquery():
        """Scalar subquery: cheapest active SKU price for a product."""
        return (
            select(func.min(func.coalesce(OrmSKU.price, OrmVariant.default_price)))
            .join(OrmVariant, OrmVariant.id == OrmSKU.variant_id)
            .where(
                OrmSKU.product_id == OrmProduct.id,
                OrmSKU.is_active.is_(True),
                OrmSKU.deleted_at.is_(None),
                OrmVariant.deleted_at.is_(None),
                func.coalesce(OrmSKU.price, OrmVariant.default_price).is_not(None),
            )
            .correlate(OrmProduct)
            .scalar_subquery()
        )

    @staticmethod
    def _has_stock_exists():
        """EXISTS: product has at least one active priced SKU."""
        return exists(
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

    @staticmethod
    def _attr_filter_exists(value_ids: list[uuid.UUID]):
        """EXISTS subquery for a resolved attribute filter (on OrmProduct)."""
        return exists(
            select(literal(1))
            .select_from(OrmProductAttributeValue)
            .where(
                OrmProductAttributeValue.product_id == OrmProduct.id,
                OrmProductAttributeValue.attribute_value_id.in_(value_ids),
            )
        ).correlate(OrmProduct)

    # ------------------------------------------------------------------
    # Attribute facet counts
    # ------------------------------------------------------------------

    async def _count_attr_values(
        self,
        *,
        category_id: uuid.UUID,
        attribute_id: uuid.UUID,
        brand_ids: list[uuid.UUID] | None,
        price_min: int | None,
        price_max: int | None,
        in_stock: bool | None,
        attr_filters: dict[str, list[uuid.UUID]],
    ) -> dict[uuid.UUID, int]:
        """COUNT products grouped by attribute_value_id for one attribute.

        Uses aliased PAV for the outer FROM so that attribute filter EXISTS
        subqueries don't clash.
        """
        PavOuter = aliased(OrmProductAttributeValue)

        stmt = (
            select(
                PavOuter.attribute_value_id,
                func.count(PavOuter.product_id.distinct()).label("cnt"),
            )
            .join(OrmProduct, OrmProduct.id == PavOuter.product_id)
            .where(
                PavOuter.attribute_id == attribute_id,
                OrmProduct.primary_category_id == category_id,
                *self._base_where(),
            )
            .group_by(PavOuter.attribute_value_id)
        )

        if brand_ids:
            stmt = stmt.where(OrmProduct.brand_id.in_(brand_ids))

        if price_min is not None or price_max is not None:
            mp = self._min_price_subquery()
            if price_min is not None:
                stmt = stmt.where(mp >= price_min)
            if price_max is not None:
                stmt = stmt.where(mp <= price_max)

        if in_stock is True:
            stmt = stmt.where(self._has_stock_exists())

        for vids in attr_filters.values():
            if vids:
                stmt = stmt.where(self._attr_filter_exists(vids))

        result = await self._session.execute(stmt)
        return {row.attribute_value_id: row.cnt for row in result.all()}

    # ------------------------------------------------------------------
    # Brand facet counts
    # ------------------------------------------------------------------

    async def _count_brands(
        self,
        *,
        category_id: uuid.UUID,
        price_min: int | None,
        price_max: int | None,
        in_stock: bool | None,
        attr_filters: dict[str, list[uuid.UUID]],
    ) -> list[BrandFacetValueReadModel]:
        stmt = (
            select(
                OrmProduct.brand_id,
                OrmBrand.name.label("brand_name"),
                OrmBrand.slug.label("brand_slug"),
                OrmBrand.logo_url.label("brand_logo_url"),
                func.count(OrmProduct.id.distinct()).label("cnt"),
            )
            .join(OrmBrand, OrmBrand.id == OrmProduct.brand_id)
            .where(
                OrmProduct.primary_category_id == category_id,
                *self._base_where(),
            )
            .group_by(
                OrmProduct.brand_id,
                OrmBrand.name,
                OrmBrand.slug,
                OrmBrand.logo_url,
            )
        )

        if price_min is not None or price_max is not None:
            mp = self._min_price_subquery()
            if price_min is not None:
                stmt = stmt.where(mp >= price_min)
            if price_max is not None:
                stmt = stmt.where(mp <= price_max)

        if in_stock is True:
            stmt = stmt.where(self._has_stock_exists())

        for vids in attr_filters.values():
            if vids:
                stmt = stmt.where(self._attr_filter_exists(vids))

        result = await self._session.execute(stmt)
        return [
            BrandFacetValueReadModel(
                brand_id=row.brand_id,
                name=row.brand_name,
                slug=row.brand_slug,
                logo_url=row.brand_logo_url,
                count=row.cnt,
            )
            for row in result.all()
        ]

    # ------------------------------------------------------------------
    # Price range
    # ------------------------------------------------------------------

    async def _compute_price_range(
        self,
        *,
        category_id: uuid.UUID,
        brand_ids: list[uuid.UUID] | None,
        in_stock: bool | None,
        attr_filters: dict[str, list[uuid.UUID]],
    ) -> PriceRangeReadModel | None:
        """Min/max of cheapest-SKU prices (post_filter: excludes price)."""
        mp = self._min_price_subquery()
        stmt = (
            select(
                func.min(mp).label("range_min"),
                func.max(mp).label("range_max"),
            )
            .select_from(OrmProduct)
            .where(
                OrmProduct.primary_category_id == category_id,
                *self._base_where(),
            )
        )

        if brand_ids:
            stmt = stmt.where(OrmProduct.brand_id.in_(brand_ids))

        if in_stock is True:
            stmt = stmt.where(self._has_stock_exists())

        for vids in attr_filters.values():
            if vids:
                stmt = stmt.where(self._attr_filter_exists(vids))

        row = (await self._session.execute(stmt)).one_or_none()
        if row is None or row.range_min is None:
            return None
        return PriceRangeReadModel(min_price=row.range_min, max_price=row.range_max)

    # ------------------------------------------------------------------
    # Total count
    # ------------------------------------------------------------------

    async def _count_total(
        self,
        *,
        category_id: uuid.UUID,
        brand_ids: list[uuid.UUID] | None,
        price_min: int | None,
        price_max: int | None,
        in_stock: bool | None,
        attr_filters: dict[str, list[uuid.UUID]],
    ) -> int:
        stmt = select(func.count(OrmProduct.id)).where(
            OrmProduct.primary_category_id == category_id,
            *self._base_where(),
        )

        if brand_ids:
            stmt = stmt.where(OrmProduct.brand_id.in_(brand_ids))

        if price_min is not None or price_max is not None:
            mp = self._min_price_subquery()
            if price_min is not None:
                stmt = stmt.where(mp >= price_min)
            if price_max is not None:
                stmt = stmt.where(mp <= price_max)

        if in_stock is True:
            stmt = stmt.where(self._has_stock_exists())

        for vids in attr_filters.values():
            if vids:
                stmt = stmt.where(self._attr_filter_exists(vids))

        return (await self._session.execute(stmt)).scalar_one()

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _query_hash(query: ComputeFacetsQuery) -> str:
        af = None
        if query.attribute_filters:
            af = {k: sorted(v) for k, v in sorted(query.attribute_filters.items())}
        parts = {
            "c": str(query.category_id),
            "b": sorted(str(b) for b in (query.brand_ids or [])),
            "pn": query.price_min,
            "px": query.price_max,
            "is": query.in_stock,
            "af": af,
        }
        return hashlib.md5(
            json.dumps(parts, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

    async def _cache_result(self, key: str, result: FacetResultReadModel) -> None:
        try:
            payload = json.dumps(result.model_dump(mode="json"), default=str)
            await self._cache.set(key, payload, ttl=STOREFRONT_FACET_CACHE_TTL)
        except Exception:
            self._logger.warning("facet_cache_write_failed", key=key)
