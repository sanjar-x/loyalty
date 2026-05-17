"""SQLAlchemy implementation of :class:`IProductHydrationReader`.

Builds an :class:`ProductIndexDoc` from PostgreSQL by composing several
focused queries (basics / cheapest SKU / counters / attribute values /
primary image) instead of one giant LATERAL join. The trade-off is
extra round-trips per product (≈6) for code simplicity / debuggability;
the indexer is off the request path and the initial reindex tooling
controls its own concurrency, so the overhead is acceptable.

The priceability rules (cheapest active priced SKU, ADR-005 statuses)
mirror :class:`SearchProductsHandler._build_enriched_subquery` so the
ES doc carries the same effective_price / in_stock signals the
storefront PLP renders.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import case, exists, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.ports import (
    IProductHydrationReader,
    ProductIndexDoc,
)
from src.modules.catalog.domain.value_objects import MediaRole
from src.modules.catalog.infrastructure.models import (
    SKU as OrmSKU,
)
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
)
from src.modules.catalog.infrastructure.models import (
    AttributeValue as OrmAttributeValue,
)
from src.modules.catalog.infrastructure.models import (
    Brand as OrmBrand,
)
from src.modules.catalog.infrastructure.models import (
    Category as OrmCategory,
)
from src.modules.catalog.infrastructure.models import (
    MediaAsset as OrmMediaAsset,
)
from src.modules.catalog.infrastructure.models import (
    Product as OrmProduct,
)
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValue as OrmProductAttributeValue,
)
from src.modules.catalog.infrastructure.models import (
    ProductVariant as OrmVariant,
)
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier


class ProductHydrationAdapter(IProductHydrationReader):
    """SQLAlchemy reader producing ES-ready product documents."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # IProductHydrationReader
    # ------------------------------------------------------------------

    async def get(self, product_id: uuid.UUID) -> ProductIndexDoc | None:
        basics = await self._fetch_basics(product_id)
        if basics is None:
            return None
        return await self._build_doc(basics)

    async def iter_indexable(  # type: ignore[override]
        self, *, batch_size: int = 500
    ) -> AsyncIterator[ProductIndexDoc]:
        """Keyset pagination over non-deleted products.

        Yields products in ``product_id`` ascending order so the indexer
        can resume from a checkpoint and ES does not race with newly
        inserted rows that happen to fall earlier on a created_at sort.
        """
        cursor: uuid.UUID | None = None
        while True:
            batch = await self._fetch_batch(after_id=cursor, limit=batch_size)
            if not batch:
                return
            for row in batch:
                yield await self._build_doc(row)
            cursor = batch[-1].product_id

    # ------------------------------------------------------------------
    # Stage 1 — basics (product + brand + supplier + primary_category)
    # ------------------------------------------------------------------

    async def _fetch_basics(self, product_id: uuid.UUID) -> Any | None:
        stmt = self._basics_stmt().where(OrmProduct.id == product_id)
        return (await self._session.execute(stmt)).one_or_none()

    async def _fetch_batch(
        self, *, after_id: uuid.UUID | None, limit: int
    ) -> list[Any]:
        stmt = self._basics_stmt().where(OrmProduct.deleted_at.is_(None))
        if after_id is not None:
            stmt = stmt.where(OrmProduct.id > after_id)
        stmt = stmt.order_by(OrmProduct.id.asc()).limit(limit)
        return list((await self._session.execute(stmt)).all())

    def _basics_stmt(self):
        return (
            select(
                OrmProduct.id.label("product_id"),
                OrmProduct.slug,
                OrmProduct.status,
                OrmProduct.is_visible,
                OrmProduct.deleted_at,
                OrmProduct.title_i18n,
                OrmProduct.description_i18n,
                OrmProduct.tags,
                OrmProduct.country_of_origin,
                OrmProduct.source_url,
                OrmProduct.popularity_score,
                OrmProduct.published_at,
                OrmProduct.created_at,
                OrmProduct.updated_at,
                OrmProduct.brand_id,
                OrmProduct.primary_category_id,
                OrmProduct.supplier_id,
                OrmBrand.name.label("brand_name"),
                OrmBrand.slug.label("brand_slug"),
                OrmBrand.logo_url.label("brand_logo_url"),
                OrmSupplier.type.label("supplier_type"),
                OrmCategory.full_slug.label("category_full_slug"),
                OrmCategory.name_i18n.label("category_name_i18n"),
            )
            .outerjoin(OrmBrand, OrmBrand.id == OrmProduct.brand_id)
            .outerjoin(OrmSupplier, OrmSupplier.id == OrmProduct.supplier_id)
            .outerjoin(OrmCategory, OrmCategory.id == OrmProduct.primary_category_id)
        )

    # ------------------------------------------------------------------
    # Stage 2 — cheapest SKU (ADR-005 priceability)
    # ------------------------------------------------------------------

    async def _fetch_cheapest_sku(
        self, product_id: uuid.UUID
    ) -> tuple[int | None, int | None, str | None]:
        effective_price = case(
            (OrmSKU.pricing_status == "priced", OrmSKU.selling_price),
            else_=func.coalesce(OrmSKU.price, OrmVariant.default_price),
        )
        stmt = (
            select(
                effective_price.label("effective_price"),
                OrmSKU.compare_at_price.label("compare_at_price"),
                func.coalesce(OrmSKU.selling_currency, OrmSKU.currency).label(
                    "currency"
                ),
            )
            .join(OrmVariant, OrmVariant.id == OrmSKU.variant_id)
            .where(
                OrmSKU.product_id == product_id,
                OrmSKU.is_active.is_(True),
                OrmSKU.deleted_at.is_(None),
                OrmVariant.deleted_at.is_(None),
                OrmSKU.pricing_status.in_(("legacy", "priced", "pending")),
                effective_price.is_not(None),
            )
            .order_by(effective_price.asc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).one_or_none()
        if row is None:
            return None, None, None
        return (
            int(row.effective_price) if row.effective_price is not None else None,
            int(row.compare_at_price) if row.compare_at_price is not None else None,
            row.currency,
        )

    # ------------------------------------------------------------------
    # Stage 3 — counters (variants, SKUs, in_stock, sku_codes, titles)
    # ------------------------------------------------------------------

    async def _fetch_counters(
        self, product_id: uuid.UUID
    ) -> tuple[int, int, bool, tuple[str, ...], dict[str, str | None]]:
        variant_count_stmt = select(func.count(OrmVariant.id)).where(
            OrmVariant.product_id == product_id,
            OrmVariant.deleted_at.is_(None),
        )
        variant_count = (await self._session.execute(variant_count_stmt)).scalar() or 0

        sku_count_stmt = select(func.count(OrmSKU.id)).where(
            OrmSKU.product_id == product_id,
            OrmSKU.deleted_at.is_(None),
        )
        sku_count = (await self._session.execute(sku_count_stmt)).scalar() or 0

        effective_price = case(
            (OrmSKU.pricing_status == "priced", OrmSKU.selling_price),
            else_=func.coalesce(OrmSKU.price, OrmVariant.default_price),
        )
        in_stock_stmt = select(
            exists(
                select(literal(1))
                .select_from(OrmSKU)
                .join(OrmVariant, OrmVariant.id == OrmSKU.variant_id)
                .where(
                    OrmSKU.product_id == product_id,
                    OrmSKU.is_active.is_(True),
                    OrmSKU.deleted_at.is_(None),
                    OrmVariant.deleted_at.is_(None),
                    OrmSKU.pricing_status.in_(("legacy", "priced", "pending")),
                    effective_price.is_not(None),
                )
            )
        )
        in_stock = bool((await self._session.execute(in_stock_stmt)).scalar())

        sku_codes_stmt = select(OrmSKU.sku_code).where(
            OrmSKU.product_id == product_id,
            OrmSKU.deleted_at.is_(None),
        )
        sku_codes = tuple(
            str(row.sku_code)
            for row in (await self._session.execute(sku_codes_stmt)).all()
        )

        # Variant titles aggregated as a flat ", "-joined string per locale.
        variants_stmt = select(OrmVariant.name_i18n).where(
            OrmVariant.product_id == product_id,
            OrmVariant.deleted_at.is_(None),
        )
        ru_titles: list[str] = []
        en_titles: list[str] = []
        for row in (await self._session.execute(variants_stmt)).all():
            i18n = row.name_i18n or {}
            if i18n.get("ru"):
                ru_titles.append(str(i18n["ru"]))
            if i18n.get("en"):
                en_titles.append(str(i18n["en"]))
        variant_titles = {
            "ru": ", ".join(ru_titles) if ru_titles else None,
            "en": ", ".join(en_titles) if en_titles else None,
        }

        return int(variant_count), int(sku_count), in_stock, sku_codes, variant_titles

    # ------------------------------------------------------------------
    # Stage 4 — attribute values (nested + searchable flatten)
    # ------------------------------------------------------------------

    async def _fetch_attribute_values(
        self, product_id: uuid.UUID
    ) -> tuple[tuple[dict[str, Any], ...], str | None, str | None, str | None]:
        stmt = (
            select(
                OrmAttribute.code.label("attribute_code"),
                OrmAttribute.slug.label("attribute_slug"),
                OrmAttribute.is_searchable.label("is_searchable"),
                OrmAttributeValue.code.label("value_code"),
                OrmAttributeValue.slug.label("value_slug"),
                OrmAttributeValue.value_i18n.label("value_i18n"),
                OrmAttributeValue.value_group.label("value_group"),
                OrmAttributeValue.search_aliases.label("search_aliases"),
            )
            .select_from(OrmProductAttributeValue)
            .join(
                OrmAttribute,
                OrmAttribute.id == OrmProductAttributeValue.attribute_id,
            )
            .join(
                OrmAttributeValue,
                OrmAttributeValue.id == OrmProductAttributeValue.attribute_value_id,
            )
            .where(
                OrmProductAttributeValue.product_id == product_id,
                OrmAttributeValue.is_active.is_(True),
            )
        )
        rows = (await self._session.execute(stmt)).all()

        nested: list[dict[str, Any]] = []
        searchable_ru: list[str] = []
        searchable_en: list[str] = []
        aliases: list[str] = []
        for row in rows:
            value_i18n = row.value_i18n or {}
            label_ru = str(value_i18n.get("ru")) if value_i18n.get("ru") else None
            label_en = str(value_i18n.get("en")) if value_i18n.get("en") else None
            nested.append(
                {
                    "attribute_code": row.attribute_code,
                    "attribute_slug": row.attribute_slug,
                    "value_code": row.value_code,
                    "value_slug": row.value_slug,
                    "value_label_ru": label_ru,
                    "value_label_en": label_en,
                    "value_group": row.value_group,
                }
            )
            if row.is_searchable:
                if label_ru:
                    searchable_ru.append(label_ru)
                if label_en:
                    searchable_en.append(label_en)
            for alias in row.search_aliases or []:
                if alias:
                    aliases.append(str(alias))

        return (
            tuple(nested),
            " ".join(searchable_ru) if searchable_ru else None,
            " ".join(searchable_en) if searchable_en else None,
            " ".join(aliases) if aliases else None,
        )

    # ------------------------------------------------------------------
    # Stage 5 — primary image
    # ------------------------------------------------------------------

    async def _fetch_primary_image(
        self, product_id: uuid.UUID
    ) -> tuple[str | None, list[dict[str, Any]] | None]:
        stmt = (
            select(
                OrmMediaAsset.url,
                OrmMediaAsset.image_variants,
            )
            .where(
                OrmMediaAsset.product_id == product_id,
                OrmMediaAsset.url.is_not(None),
            )
            .order_by(
                OrmMediaAsset.variant_id.is_not(None).asc(),
                (OrmMediaAsset.role != MediaRole.MAIN).asc(),
                OrmMediaAsset.sort_order.asc(),
                OrmMediaAsset.created_at.asc(),
            )
            .limit(1)
        )
        row = (await self._session.execute(stmt)).one_or_none()
        if row is None:
            return None, None
        return row.url, row.image_variants

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    async def _build_doc(self, basics: Any) -> ProductIndexDoc:
        product_id = basics.product_id

        price, compare_at, currency = await self._fetch_cheapest_sku(product_id)
        (
            variant_count,
            sku_count,
            in_stock,
            sku_codes,
            variant_titles,
        ) = await self._fetch_counters(product_id)
        (
            attribute_values,
            searchable_ru,
            searchable_en,
            aliases,
        ) = await self._fetch_attribute_values(product_id)
        image_url, image_variants = await self._fetch_primary_image(product_id)

        title_i18n: dict[str, Any] = basics.title_i18n or {}
        description_i18n: dict[str, Any] = basics.description_i18n or {}
        category_i18n: dict[str, Any] = basics.category_name_i18n or {}
        tags: tuple[str, ...] = tuple(basics.tags or ())

        return ProductIndexDoc(
            product_id=product_id,
            slug=basics.slug,
            status=str(
                basics.status.value
                if hasattr(basics.status, "value")
                else basics.status
            ),
            is_visible=bool(basics.is_visible),
            deleted=basics.deleted_at is not None,
            supplier_id=basics.supplier_id,
            supplier_type=(
                basics.supplier_type.value
                if basics.supplier_type is not None
                and hasattr(basics.supplier_type, "value")
                else basics.supplier_type
            ),
            brand_id=basics.brand_id,
            brand_name=basics.brand_name,
            brand_slug=basics.brand_slug,
            brand_logo_url=basics.brand_logo_url,
            primary_category_id=basics.primary_category_id,
            category_ids=(
                (basics.primary_category_id,) if basics.primary_category_id else ()
            ),
            category_full_slug=basics.category_full_slug,
            category_names_ru=str(category_i18n.get("ru"))
            if category_i18n.get("ru")
            else None,
            category_names_en=str(category_i18n.get("en"))
            if category_i18n.get("en")
            else None,
            title_ru=str(title_i18n.get("ru")) if title_i18n.get("ru") else None,
            title_en=str(title_i18n.get("en")) if title_i18n.get("en") else None,
            description_ru=(
                str(description_i18n.get("ru")) if description_i18n.get("ru") else None
            ),
            description_en=(
                str(description_i18n.get("en")) if description_i18n.get("en") else None
            ),
            tags=tags,
            tags_text=" ".join(tags) if tags else None,
            country_of_origin=basics.country_of_origin,
            source_url=basics.source_url,
            effective_price=price,
            compare_at_price=compare_at,
            currency=currency,
            in_stock=in_stock,
            variant_count=variant_count,
            sku_count=sku_count,
            sku_codes=sku_codes,
            popularity_score=float(basics.popularity_score or 0),
            published_at=basics.published_at.isoformat()
            if basics.published_at
            else None,
            created_at=basics.created_at.isoformat() if basics.created_at else None,
            updated_at=basics.updated_at.isoformat() if basics.updated_at else None,
            image_url=image_url,
            image_variants=image_variants,
            variant_titles_ru=variant_titles["ru"],
            variant_titles_en=variant_titles["en"],
            searchable_attribute_text_ru=searchable_ru,
            searchable_attribute_text_en=searchable_en,
            searchable_attribute_aliases=aliases,
            attribute_values=attribute_values,
        )
