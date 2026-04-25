"""
Query handler: storefront full-text product search.

Public read-only endpoint returning lightweight product cards matching a
search query.  Uses PostgreSQL tsvector/tsquery full-text search with the
``catalog_product_search_vector`` function (created in Alembic migration).

CQRS read side — queries ORM directly, returns read models.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import Float, and_, case, exists, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.constants import (
    STOREFRONT_SEARCH_CACHE_TTL,
    storefront_search_cache_key,
)
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
from src.shared.cache_keys import read_storefront_product_generation
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.pagination import CursorPage, decode_cursor, encode_cursor

# Regex: keep only word characters (Unicode-aware) and spaces.
_SEARCH_TOKEN_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _build_tsquery(raw_query: str) -> str:
    """Build a safe tsquery string from user input.

    Tokenises the input, escapes special characters, and appends a prefix
    operator (``*``) to the last token so partial words match (typeahead).
    Tokens are combined with ``&`` (AND).
    """
    cleaned = _SEARCH_TOKEN_RE.sub(" ", raw_query)
    tokens = cleaned.split()
    if not tokens:
        return ""
    # Quote each token and join with &. Last token gets prefix :*.
    safe = [t.strip() for t in tokens if t.strip()]
    if not safe:
        return ""
    parts = [f"'{t}'" for t in safe[:-1]]
    parts.append(f"'{safe[-1]}':*")
    return " & ".join(parts)


@dataclass(frozen=True)
class SearchProductsQuery:
    """Parameters for storefront product search."""

    q: str
    category_id: uuid.UUID | None = None
    brand_ids: list[uuid.UUID] | None = None
    price_min: int | None = None
    price_max: int | None = None
    in_stock: bool | None = None
    attribute_filters: dict[str, list[str]] | None = None
    sort: str = "relevant"  # relevant, popular, newest, price_asc, price_desc
    limit: int = 24
    cursor: str | None = None
    include_total: bool = False


class SearchProductsHandler:
    """Full-text product search for the storefront."""

    # The SQL function from the migration.
    _SEARCH_VECTOR = func.catalog_product_search_vector(
        OrmProduct.title_i18n,
        OrmProduct.description_i18n,
        OrmProduct.tags,
    )

    def __init__(
        self,
        session: AsyncSession,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._session = session
        self._cache = cache
        self._logger = logger.bind(handler="SearchProductsHandler")

    async def handle(
        self, query: SearchProductsQuery
    ) -> CursorPage[StorefrontProductCardReadModel]:
        generation = await read_storefront_product_generation(self._cache)
        cache_key = storefront_search_cache_key(self._query_hash(query, generation))
        cached = await self._cache.get(cache_key)
        if cached:
            return self._deserialize_cache(cached)

        tsquery_str = _build_tsquery(query.q)
        if not tsquery_str:
            return CursorPage(items=[], has_next=False, next_cursor=None, total=0)

        tsquery_lit = text(f"$${tsquery_str}$$")
        # Combine tsqueries from all three configs used in the tsvector function
        # so that Russian-stemmed, English-stemmed, and simple lexemes all match.
        tsquery = (
            func.to_tsquery("russian", tsquery_lit)
            .op("||")(func.to_tsquery("english", tsquery_lit))
            .op("||")(func.to_tsquery("simple", tsquery_lit))
        )

        resolved_attr = (
            await self._resolve_attribute_filters(query.attribute_filters)
            if query.attribute_filters
            else None
        )

        enriched = self._build_enriched_subquery(query, tsquery, resolved_attr)

        stmt = select(enriched)
        stmt = self._apply_sorting(stmt, enriched, query.sort)
        stmt = self._apply_cursor(stmt, enriched, query)
        stmt = stmt.limit(query.limit + 1)

        # ``to_tsquery`` raises ProgrammingError on malformed input
        # (lone operators, empty quoted tokens). Return empty results
        # rather than 500-ing the public search endpoint.
        try:
            result = await self._session.execute(stmt)
            rows = result.all()
        except Exception as exc:
            self._logger.warning("search_tsquery_failed", error=str(exc), q=query.q)
            return CursorPage(items=[], has_next=False, next_cursor=None, total=0)

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
            count_sub = self._build_enriched_subquery(query, tsquery, resolved_attr)
            count_stmt = select(func.count()).select_from(count_sub)
            try:
                total = (await self._session.execute(count_stmt)).scalar_one()
            except Exception as exc:
                self._logger.warning(
                    "search_count_failed", error=str(exc), q=query.q
                )
                total = 0

        page = CursorPage(
            items=items,
            has_next=has_next,
            next_cursor=next_cursor,
            total=total,
        )
        await self._cache_result(cache_key, page)
        return page

    # ------------------------------------------------------------------
    # Enriched subquery
    # ------------------------------------------------------------------

    def _build_enriched_subquery(self, query, tsquery, resolved_attr_filters=None):
        search_vector = self._SEARCH_VECTOR
        rank_expr = func.ts_rank_cd(search_vector, tsquery).cast(Float).label("rank")

        # ADR-005 — same priceability shape as ``list_storefront_products``:
        # autonomously priced SKUs win over the legacy manual price; SKUs
        # in non-priceable failure statuses are excluded so search hits
        # always carry the same price the customer sees on the PLP/PDP.
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

        # Best image to render as product card thumbnail.
        # Priority: product-level (variant_id IS NULL) before variant-level,
        # MAIN before other roles, lowest sort_order, earliest created_at.
        # Variant-level fallback matters when products carry per-variant MAIN
        # images and have no product-scoped media.
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
                rank_expr,
            )
            .join(OrmBrand, OrmBrand.id == OrmProduct.brand_id)
            .outerjoin(OrmSupplier, OrmSupplier.id == OrmProduct.supplier_id)
            .outerjoin(cheapest_sku, literal(True))
            .outerjoin(primary_image, literal(True))
            .where(
                OrmProduct.status == ProductStatus.PUBLISHED,
                OrmProduct.is_visible.is_(True),
                OrmProduct.deleted_at.is_(None),
                search_vector.op("@@")(tsquery),
            )
        )

        if query.category_id:
            base = base.where(OrmProduct.primary_category_id == query.category_id)

        if query.brand_ids:
            base = base.where(OrmProduct.brand_id.in_(query.brand_ids))

        if query.price_min is not None:
            base = base.where(cheapest_sku.c.effective_price >= query.price_min)

        if query.price_max is not None:
            base = base.where(cheapest_sku.c.effective_price <= query.price_max)

        if query.in_stock is True:
            base = base.where(cheapest_sku.c.effective_price.is_not(None))

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
    def _apply_sorting(stmt, enriched, sort: str):
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
        if sort == "popular":
            return stmt.order_by(
                enriched.c.popularity_score.desc().nullslast(),
                enriched.c.product_id.desc(),
            )
        # Default: relevant (FTS rank)
        return stmt.order_by(
            enriched.c.rank.desc(),
            enriched.c.product_id.desc(),
        )

    # ------------------------------------------------------------------
    # Cursor pagination
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_cursor(stmt, enriched, query: SearchProductsQuery):
        if not query.cursor:
            return stmt

        cursor_sort_val, cursor_id = decode_cursor(query.cursor)
        pk = enriched.c.product_id
        sort = query.sort

        # NULL-safe keyset for ``nullslast()`` orders — see PLP handler.
        def _nullslast_keyset(col, op_strict: str):
            strict = (
                (col > cursor_sort_val) if op_strict == ">" else (col < cursor_sort_val)
            )
            return (
                (col.is_not(None) & strict)
                | (col.is_not(None) & (col == cursor_sort_val) & (pk < cursor_id))
                | (col.is_(None) & (pk < cursor_id))
            )

        if sort == "newest":
            stmt = stmt.where(_nullslast_keyset(enriched.c.published_at, "<"))
        elif sort == "price_asc":
            stmt = stmt.where(_nullslast_keyset(enriched.c.effective_price, ">"))
        elif sort == "price_desc":
            stmt = stmt.where(_nullslast_keyset(enriched.c.effective_price, "<"))
        elif sort == "popular":
            stmt = stmt.where(_nullslast_keyset(enriched.c.popularity_score, "<"))
        else:
            # Relevance rank — float, no NULLs (ts_rank_cd never returns NULL).
            col = enriched.c.rank
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
        if sort == "popular":
            return row.popularity_score
        # relevance: round for stable cursor
        return round(float(row.rank), 6) if row.rank is not None else 0.0

    # ------------------------------------------------------------------
    # Row → ReadModel mapping (same as PLP)
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
    # Attribute filter resolution (same as PLP)
    # ------------------------------------------------------------------

    async def _resolve_attribute_filters(
        self,
        attribute_filters: dict[str, list[str]],
    ) -> dict[str, list[uuid.UUID]] | None:
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
    def _query_hash(query: SearchProductsQuery, generation: int = 0) -> str:
        af = None
        if query.attribute_filters:
            af = {k: sorted(v) for k, v in sorted(query.attribute_filters.items())}
        parts = {
            "q": query.q.lower().strip(),
            "c": str(query.category_id) if query.category_id else None,
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
            await self._cache.set(key, payload, ttl=STOREFRONT_SEARCH_CACHE_TTL)
        except Exception:
            self._logger.warning("search_cache_write_failed", key=key)

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
