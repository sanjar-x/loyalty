"""
Query handler: storefront product listing (PLP).

Public read-only endpoint returning lightweight product cards for the
customer-facing catalogue grid.  Supports category-scoped browsing,
multi-filter (brand, price range, stock), cursor pagination, and
Redis caching.

CQRS read side — queries ORM directly, returns read models.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass

from sqlalchemy import Select, and_, case, exists, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.constants import (
    STOREFRONT_PLP_CACHE_TTL,
    storefront_plp_cache_key,
)
from src.shared.cache_keys import read_storefront_product_generation
from src.modules.catalog.application.queries.read_models import (
    StorefrontBrandReadModel,
    StorefrontImageReadModel,
    StorefrontMoneyReadModel,
    StorefrontProductCardReadModel,
    StorefrontSupplierReadModel,
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
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValue as OrmProductAttributeValue,
)
from src.modules.catalog.infrastructure.models import ProductVariant as OrmVariant
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.pagination import CursorPage, decode_cursor, encode_cursor


@dataclass(frozen=True)
class StorefrontProductListQuery:
    """Parameters for storefront product listing.

    Attributes:
        category_id: Required — only products in this category are returned.
        brand_ids: Optional brand filter (OR semantics).
        price_min: Minimum price filter (smallest currency unit, inclusive).
        price_max: Maximum price filter (smallest currency unit, inclusive).
        in_stock: When True, only products with ≥1 active priced SKU.
        sort: Sort order — popular (default), newest, price_asc, price_desc.
        limit: Page size (1–48, default 24).
        cursor: Opaque cursor from previous page.
        include_total: Include total count (slower, for first page only).
    """

    category_id: uuid.UUID
    brand_ids: list[uuid.UUID] | None = None
    price_min: int | None = None
    price_max: int | None = None
    in_stock: bool | None = None
    attribute_filters: dict[str, list[str]] | None = None
    sort: str = "popular"
    limit: int = 24
    cursor: str | None = None
    include_total: bool = False


class ListStorefrontProductsHandler:
    """Fetch a cursor-paginated product card list for the storefront."""

    _EFFECTIVE_PRICE = func.coalesce(OrmSKU.price, OrmVariant.default_price)

    def __init__(
        self,
        session: AsyncSession,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._session = session
        self._cache = cache
        self._logger = logger.bind(handler="ListStorefrontProductsHandler")

    async def handle(
        self, query: StorefrontProductListQuery
    ) -> CursorPage[StorefrontProductCardReadModel]:
        generation = await read_storefront_product_generation(self._cache)
        cache_key = storefront_plp_cache_key(self._query_hash(query, generation))
        cached = await self._cache.get(cache_key)
        if cached:
            return self._deserialize_cache(cached)

        # Resolve attribute slug filters → value IDs for efficient EXISTS.
        resolved_attr = (
            await self._resolve_attribute_filters(query.attribute_filters)
            if query.attribute_filters
            else None
        )

        # Build the "enriched product" subquery with computed columns.
        enriched = self._build_enriched_subquery(query, resolved_attr)

        # Apply sorting to the enriched subquery.
        stmt = select(enriched)
        stmt = self._apply_sorting(stmt, enriched, query.sort)

        # Apply cursor-based keyset pagination.
        stmt = self._apply_cursor(stmt, enriched, query)

        # Fetch limit + 1 to detect has_next.
        stmt = stmt.limit(query.limit + 1)
        result = await self._session.execute(stmt)
        rows = result.all()

        has_next = len(rows) > query.limit
        rows = rows[: query.limit]

        items = [self._row_to_card(row) for row in rows]

        next_cursor: str | None = None
        if has_next and rows:
            last = rows[-1]
            sort_val = self._extract_sort_value(last, query.sort)
            next_cursor = encode_cursor(sort_val, last.product_id)

        total: int | None = None
        if query.include_total:
            count_sub = self._build_enriched_subquery(query, resolved_attr)
            count_stmt = select(func.count()).select_from(count_sub)
            total = (await self._session.execute(count_stmt)).scalar_one()

        page = CursorPage(
            items=items,
            has_next=has_next,
            next_cursor=next_cursor,
            total=total,
        )

        await self._cache_result(cache_key, page)
        return page

    # ------------------------------------------------------------------
    # Enriched subquery: product + cheapest SKU + brand + primary image
    # ------------------------------------------------------------------

    def _build_enriched_subquery(
        self,
        query: StorefrontProductListQuery,
        resolved_attr_filters: dict[str, list[uuid.UUID]] | None = None,
    ):
        """Build a subquery with product data + computed columns.

        Uses a lateral join to find the cheapest active SKU per product,
        resolving effective price as COALESCE(sku.price, variant.default_price).
        """
        # Lateral: best image to render as product card thumbnail.
        # Priority:
        #   1. product-level media (variant_id IS NULL) before variant-level
        #   2. role=MAIN before other roles
        #   3. lowest sort_order, then earliest created_at
        # Variant-level fallback matters when products carry per-variant MAIN
        # images (a valid pattern, enforced by uix_media_single_main_per_variant)
        # and have no product-scoped media — otherwise the card would render
        # without a thumbnail.
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

        # Lateral: cheapest sellable SKU per product (ADR-005).
        # Priority of price columns:
        #   1. ``selling_price`` when ``pricing_status='priced'`` —
        #      output of the autonomous pricing pipeline.
        #   2. legacy ``sku.price`` (manual override).
        #   3. ``variant.default_price`` (variant-level default).
        # SKUs in non-priceable failure statuses
        # (``stale_fx`` / ``missing_purchase_price`` / ``formula_error``)
        # are dropped from the candidate set so the storefront never
        # surfaces an incorrectly-priced item.
        effective_price_expr = case(
            (
                OrmSKU.pricing_status == "priced",
                OrmSKU.selling_price,
            ),
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

        # Variant count subquery
        variant_count_sub = (
            select(func.count(OrmVariant.id))
            .where(
                OrmVariant.product_id == OrmProduct.id,
                OrmVariant.deleted_at.is_(None),
            )
            .correlate(OrmProduct)
            .scalar_subquery()
        )

        # Has-stock flag: exists at least one sellable SKU. Mirrors
        # the cheapest-SKU priceability rule above so the flag and
        # the price always agree.
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

        base = (
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
                OrmProduct.status == ProductStatus.PUBLISHED,
                OrmProduct.is_visible.is_(True),
                OrmProduct.deleted_at.is_(None),
                OrmProduct.primary_category_id == query.category_id,
            )
        )

        # Optional filters
        if query.brand_ids:
            base = base.where(OrmProduct.brand_id.in_(query.brand_ids))

        if query.price_min is not None:
            base = base.where(cheapest_sku.c.effective_price >= query.price_min)

        if query.price_max is not None:
            base = base.where(cheapest_sku.c.effective_price <= query.price_max)

        if query.in_stock is True:
            base = base.where(cheapest_sku.c.effective_price.is_not(None))

        # EAV attribute filters (resolved value IDs)
        for value_ids in (resolved_attr_filters or {}).values():
            if value_ids:
                base = base.where(
                    exists(
                        select(literal(1))
                        .select_from(OrmProductAttributeValue)
                        .where(
                            OrmProductAttributeValue.product_id == OrmProduct.id,
                            OrmProductAttributeValue.attribute_value_id.in_(value_ids),
                        )
                    ).correlate(OrmProduct)
                )

        return base.subquery("enriched")

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_sorting(stmt: Select, enriched, sort: str) -> Select:
        if sort == "newest":
            return stmt.order_by(
                enriched.c.published_at.desc().nullslast(),
                enriched.c.product_id.desc(),
            )
        if sort == "price_asc":
            return stmt.order_by(
                enriched.c.effective_price.asc().nullslast(),
                enriched.c.product_id.desc(),
            )
        if sort == "price_desc":
            return stmt.order_by(
                enriched.c.effective_price.desc().nullslast(),
                enriched.c.product_id.desc(),
            )
        # Default: popular
        return stmt.order_by(
            enriched.c.popularity_score.desc().nullslast(),
            enriched.c.product_id.desc(),
        )

    # ------------------------------------------------------------------
    # Cursor-based keyset pagination
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_cursor(
        stmt: Select, enriched, query: StorefrontProductListQuery
    ) -> Select:
        if not query.cursor:
            return stmt

        cursor_sort_val, cursor_id = decode_cursor(query.cursor)
        pk = enriched.c.product_id
        sort = query.sort

        if sort == "newest":
            col = enriched.c.published_at
            stmt = stmt.where(
                (col < cursor_sort_val) | ((col == cursor_sort_val) & (pk < cursor_id))
            )
        elif sort == "price_asc":
            col = enriched.c.effective_price
            stmt = stmt.where(
                (col > cursor_sort_val) | ((col == cursor_sort_val) & (pk < cursor_id))
            )
        elif sort == "price_desc":
            col = enriched.c.effective_price
            stmt = stmt.where(
                (col < cursor_sort_val) | ((col == cursor_sort_val) & (pk < cursor_id))
            )
        else:
            col = enriched.c.popularity_score
            stmt = stmt.where(
                (col < cursor_sort_val) | ((col == cursor_sort_val) & (pk < cursor_id))
            )

        return stmt

    @staticmethod
    def _extract_sort_value(row, sort: str):
        if sort == "newest":
            return row.published_at
        if sort in ("price_asc", "price_desc"):
            return row.effective_price
        return row.popularity_score

    # ------------------------------------------------------------------
    # Row → ReadModel mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_card(row) -> StorefrontProductCardReadModel:
        image = None
        if row.image_url:
            image = StorefrontImageReadModel(
                url=row.image_url,
                image_variants=row.image_variants,
            )

        price = None
        if row.effective_price is not None:
            price = StorefrontMoneyReadModel(
                amount=row.effective_price,
                currency=row.sku_currency or "RUB",
                compare_at=row.compare_at_price,
            )

        brand = None
        if row.brand_name:
            brand = StorefrontBrandReadModel(
                id=row.brand_id,
                name=row.brand_name,
                slug=row.brand_slug or "",
                logo_url=row.brand_logo_url,
            )

        supplier = None
        supplier_type = getattr(row, "supplier_type", None)
        if supplier_type is not None:
            # ``OrmSupplier.type`` is a ``SupplierType`` enum; persist the
            # plain string value in the read model so downstream layers
            # don't need the supplier domain import.
            supplier = StorefrontSupplierReadModel(
                type=getattr(supplier_type, "value", str(supplier_type)),
            )

        return StorefrontProductCardReadModel(
            id=row.product_id,
            slug=row.slug,
            title_i18n=row.title_i18n or {},
            image=image,
            price=price,
            brand=brand,
            supplier=supplier,
            popularity_score=row.popularity_score or 0,
            published_at=row.published_at,
            variant_count=row.variant_count or 0,
            in_stock=bool(row.has_stock),
        )

    # ------------------------------------------------------------------
    # Attribute filter resolution
    # ------------------------------------------------------------------

    async def _resolve_attribute_filters(
        self,
        attribute_filters: dict[str, list[str]],
    ) -> dict[str, list[uuid.UUID]] | None:
        """Resolve attribute code+slug pairs to attribute_value_id lists.

        Single query resolves all filters.  Unknown codes/slugs are silently
        dropped so stale URLs don't break.
        """
        if not attribute_filters:
            return None

        conditions = []
        for code, slugs in attribute_filters.items():
            if slugs:
                conditions.append(
                    and_(
                        OrmAttribute.code == code,
                        OrmAttributeValue.slug.in_(slugs),
                    )
                )
        if not conditions:
            return None

        stmt = (
            select(OrmAttribute.code, OrmAttributeValue.id)
            .join(OrmAttribute, OrmAttribute.id == OrmAttributeValue.attribute_id)
            .where(OrmAttributeValue.is_active.is_(True))
            .where(or_(*conditions))
        )
        result = await self._session.execute(stmt)

        resolved: dict[str, list[uuid.UUID]] = {}
        for code, value_id in result.all():
            resolved.setdefault(code, []).append(value_id)
        return resolved or None

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _query_hash(query: StorefrontProductListQuery, generation: int = 0) -> str:
        af = None
        if query.attribute_filters:
            af = {k: sorted(v) for k, v in sorted(query.attribute_filters.items())}
        parts = {
            "c": str(query.category_id),
            "b": sorted(str(b) for b in (query.brand_ids or [])),
            "pn": query.price_min,
            "px": query.price_max,
            "is": query.in_stock,
            "s": query.sort,
            "l": query.limit,
            "cu": query.cursor,
            "t": query.include_total,
            "af": af,
            "g": generation,
        }
        return hashlib.md5(
            json.dumps(parts, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

    async def _cache_result(
        self, key: str, result: CursorPage[StorefrontProductCardReadModel]
    ) -> None:
        try:
            payload = json.dumps(
                {
                    "items": [item.model_dump(mode="json") for item in result.items],
                    "has_next": result.has_next,
                    "next_cursor": result.next_cursor,
                    "total": result.total,
                },
                default=str,
            )
            await self._cache.set(key, payload, ttl=STOREFRONT_PLP_CACHE_TTL)
        except Exception:
            self._logger.warning("plp_cache_write_failed", key=key)

    @staticmethod
    def _deserialize_cache(raw: str) -> CursorPage[StorefrontProductCardReadModel]:
        data = json.loads(raw)
        items = [
            StorefrontProductCardReadModel.model_validate(i) for i in data["items"]
        ]
        return CursorPage(
            items=items,
            has_next=data["has_next"],
            next_cursor=data.get("next_cursor"),
            total=data.get("total"),
        )
