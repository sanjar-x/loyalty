"""
Query handler: storefront product detail page (PDP).

Public read-only endpoint returning the full product detail for a
single product identified by its slug.  Includes media gallery,
variants with SKUs, attribute table, breadcrumbs, and version for ETag.

CQRS read side — queries ORM directly, returns read models.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.catalog.application.constants import (
    STOREFRONT_PDP_CACHE_TTL,
    storefront_pdp_cache_key,
)
from src.shared.cache_keys import read_storefront_product_generation
from src.modules.catalog.application.queries.breadcrumbs import BreadcrumbsBuilder
from src.modules.catalog.application.queries.read_models import (
    MoneyReadModel,
    SKUReadModel,
    StorefrontAttributeValueReadModel,
    StorefrontBrandReadModel,
    StorefrontImageReadModel,
    StorefrontMoneyReadModel,
    StorefrontProductDetailReadModel,
    StorefrontSupplierReadModel,
    StorefrontVariantOptionReadModel,
    StorefrontVariantOptionValueReadModel,
    StorefrontVariantReadModel,
    VariantAttributePairReadModel,
    resolve_sku_price,
)
from src.modules.catalog.domain.value_objects import MediaRole, ProductStatus
from src.modules.catalog.infrastructure.models import SKU as OrmSKU
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
)
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.modules.catalog.infrastructure.models import MediaAsset as OrmMediaAsset
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValue as OrmProductAttributeValue,
)
from src.modules.catalog.infrastructure.models import ProductVariant as OrmVariant
from src.modules.catalog.infrastructure.models import (
    SKUAttributeValueLink as OrmSKUAttributeValueLink,
)
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger


class GetStorefrontProductHandler:
    """Fetch full product detail for the storefront PDP."""

    def __init__(
        self,
        session: AsyncSession,
        cache: ICacheService,
        breadcrumbs: BreadcrumbsBuilder,
        logger: ILogger,
    ) -> None:
        self._session = session
        self._cache = cache
        self._breadcrumbs = breadcrumbs
        self._logger = logger.bind(handler="GetStorefrontProductHandler")

    async def handle(self, slug: str) -> StorefrontProductDetailReadModel:
        """Retrieve a published product by slug with full PDP data.

        Raises:
            NotFoundError: If no published, visible product with this slug exists.
        """
        generation = await read_storefront_product_generation(self._cache)
        cache_key = storefront_pdp_cache_key(slug, generation)
        cached = await self._cache.get(cache_key)
        if cached:
            return StorefrontProductDetailReadModel.model_validate_json(cached)

        product = await self._load_product(slug)
        if product is None:
            raise NotFoundError(
                message=f"Product '{slug}' not found",
                details={"slug": slug},
            )

        brand = await self._load_brand(product.brand_id)
        supplier = await self._load_supplier(product.supplier_id)
        media = await self._load_media(product.id)
        attributes = await self._load_attributes(product.id)
        breadcrumbs = await self._breadcrumbs.build(product.primary_category_id)

        detail = self._build_detail(
            product, brand, supplier, media, attributes, breadcrumbs
        )

        try:
            await self._cache.set(
                cache_key,
                detail.model_dump_json(),
                ttl=STOREFRONT_PDP_CACHE_TTL,
            )
        except Exception:
            self._logger.warning("pdp_cache_write_failed", slug=slug)

        return detail

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    async def _load_product(self, slug: str) -> OrmProduct | None:
        sku_attr_link = (
            selectinload(OrmProduct.variants)
            .selectinload(OrmVariant.skus)
            .selectinload(OrmSKU.attribute_values)
        )
        stmt = (
            select(OrmProduct)
            .options(
                sku_attr_link.selectinload(
                    OrmSKUAttributeValueLink.attribute  # type: ignore[attr-defined]
                ),
                sku_attr_link.selectinload(
                    OrmSKUAttributeValueLink.attribute_value  # type: ignore[attr-defined]
                ),
            )
            .where(
                OrmProduct.slug == slug,
                OrmProduct.status == ProductStatus.PUBLISHED,
                OrmProduct.is_visible.is_(True),
                OrmProduct.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_brand(self, brand_id: uuid.UUID) -> OrmBrand | None:
        stmt = select(OrmBrand).where(OrmBrand.id == brand_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_supplier(self, supplier_id: uuid.UUID | None) -> OrmSupplier | None:
        if supplier_id is None:
            return None
        stmt = select(OrmSupplier).where(OrmSupplier.id == supplier_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_media(self, product_id: uuid.UUID) -> list[OrmMediaAsset]:
        stmt = (
            select(OrmMediaAsset)
            .where(
                OrmMediaAsset.product_id == product_id,
                OrmMediaAsset.variant_id.is_(None),
            )
            .order_by(
                # MAIN first, then by sort_order
                (OrmMediaAsset.role != MediaRole.MAIN).asc(),
                OrmMediaAsset.sort_order.asc(),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _load_attributes(
        self, product_id: uuid.UUID
    ) -> list[OrmProductAttributeValue]:
        stmt = (
            select(OrmProductAttributeValue)
            .options(
                selectinload(OrmProductAttributeValue.attribute).selectinload(
                    OrmAttribute.group
                ),
                selectinload(OrmProductAttributeValue.attribute_value),
            )
            .where(OrmProductAttributeValue.product_id == product_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _build_detail(
        product: OrmProduct,
        brand: OrmBrand | None,
        supplier: OrmSupplier | None,
        media: list[OrmMediaAsset],
        attributes: list[OrmProductAttributeValue],
        breadcrumbs,
    ) -> StorefrontProductDetailReadModel:
        # Compute price from cheapest active SKU across all variants.
        min_price: int | None = None
        compare_at: int | None = None
        has_stock = False
        total_variant_count = 0

        variant_models: list[StorefrontVariantReadModel] = []
        for variant in product.variants:
            if variant.deleted_at is not None:
                continue
            total_variant_count += 1

            sku_models = []
            variant_default_price = None
            if variant.default_price is not None:
                variant_default_price = MoneyReadModel(
                    amount=variant.default_price,
                    currency=variant.default_currency or "RUB",
                )

            for sku in variant.skus:
                if sku.deleted_at is not None:
                    continue
                sku_price = (
                    MoneyReadModel(amount=sku.price, currency=sku.currency)
                    if sku.price is not None
                    else None
                )
                selling_price = (
                    MoneyReadModel(
                        amount=sku.selling_price,
                        currency=sku.selling_currency or "RUB",
                    )
                    if sku.selling_price is not None and sku.selling_currency
                    else None
                )
                pricing_status = (
                    sku.pricing_status.value
                    if hasattr(sku.pricing_status, "value")
                    else sku.pricing_status
                )
                resolved = resolve_sku_price(
                    sku_price,
                    variant_default_price,
                    selling_price=selling_price,
                    pricing_status=pricing_status,
                )

                if resolved is not None:
                    has_stock = True
                    if min_price is None or resolved.amount < min_price:
                        min_price = resolved.amount
                        compare_at = sku.compare_at_price

                pair_models = []
                for link in sku.attribute_values:
                    attr = getattr(link, "attribute", None)
                    val = getattr(link, "attribute_value", None)
                    # Skip values an admin retired — PLP filters already
                    # exclude ``is_active=False`` via _resolve_attribute_filters,
                    # so leaving them on the SKU pair would create dead-end
                    # selectors the customer can pick but never filter back to.
                    if val is not None and not getattr(val, "is_active", True):
                        continue
                    pair_models.append(
                        VariantAttributePairReadModel(
                            attribute_id=link.attribute_id,
                            attribute_value_id=link.attribute_value_id,
                            attribute_code=attr.code if attr else None,
                            attribute_name_i18n=(attr.name_i18n if attr else {}) or {},
                            value_code=val.code if val else None,
                            value_i18n=(val.value_i18n if val else {}) or {},
                            sort_order=val.sort_order if val else 0,
                        )
                    )

                sku_models.append(
                    SKUReadModel(
                        id=sku.id,
                        product_id=sku.product_id,
                        variant_id=sku.variant_id,
                        sku_code=sku.sku_code,
                        variant_hash=sku.variant_hash,
                        price=sku_price,
                        resolved_price=resolved,
                        compare_at_price=(
                            MoneyReadModel(
                                amount=sku.compare_at_price, currency=sku.currency
                            )
                            if sku.compare_at_price
                            else None
                        ),
                        is_active=sku.is_active,
                        version=sku.version,
                        deleted_at=sku.deleted_at,
                        created_at=sku.created_at,
                        updated_at=sku.updated_at,
                        variant_attributes=pair_models,
                    )
                )

            variant_models.append(
                StorefrontVariantReadModel(
                    id=variant.id,
                    name_i18n=variant.name_i18n or {},
                    sort_order=variant.sort_order,
                    skus=sku_models,
                )
            )

        # Media gallery
        media_models = [
            StorefrontImageReadModel(
                url=m.url or "",
                image_variants=m.image_variants,
            )
            for m in media
            if m.url
        ]

        # Attributes
        attr_models = []
        for pav in attributes:
            attr = pav.attribute
            val = pav.attribute_value
            group = attr.group if hasattr(attr, "group") else None
            attr_models.append(
                StorefrontAttributeValueReadModel(
                    attribute_code=attr.code,
                    attribute_name_i18n=attr.name_i18n or {},
                    value_code=val.code,
                    value_i18n=val.value_i18n or {},
                    group_code=group.code if group else None,
                    group_name_i18n=group.name_i18n if group else None,
                    sort_order=val.sort_order,
                )
            )

        # Variant options — aggregate distinct (attribute, value) pairs
        # across the product's active SKUs. Drives the variant selector
        # on PDP (size, colour, …) without requiring the client to
        # crawl every SKU.
        option_index: dict[uuid.UUID, dict] = {}
        for variant in product.variants:
            if variant.deleted_at is not None:
                continue
            for sku in variant.skus:
                if sku.deleted_at is not None or not sku.is_active:
                    continue
                for link in sku.attribute_values:
                    attr = getattr(link, "attribute", None)
                    val = getattr(link, "attribute_value", None)
                    if attr is None or val is None:
                        continue
                    # Same is_active filter as the SKU-pair projector —
                    # keeps the picker consistent with PLP filter values.
                    if not getattr(val, "is_active", True):
                        continue
                    bucket = option_index.setdefault(
                        attr.id,
                        {
                            "attribute_id": attr.id,
                            "attribute_code": attr.code,
                            "attribute_name_i18n": attr.name_i18n or {},
                            "sort_order": getattr(attr, "sort_order", 0) or 0,
                            "values": {},
                        },
                    )
                    if val.id not in bucket["values"]:
                        bucket["values"][val.id] = (
                            StorefrontVariantOptionValueReadModel(
                                value_id=val.id,
                                value_code=val.code,
                                value_i18n=val.value_i18n or {},
                                meta_data=val.meta_data or {},
                                sort_order=val.sort_order or 0,
                            )
                        )

        variant_options = [
            StorefrontVariantOptionReadModel(
                attribute_id=bucket["attribute_id"],
                attribute_code=bucket["attribute_code"],
                attribute_name_i18n=bucket["attribute_name_i18n"],
                sort_order=bucket["sort_order"],
                values=sorted(
                    bucket["values"].values(),
                    key=lambda v: (v.sort_order, v.value_code),
                ),
            )
            for bucket in sorted(
                option_index.values(),
                key=lambda b: (b["sort_order"], b["attribute_code"]),
            )
        ]

        # Brand
        brand_model = None
        if brand:
            brand_model = StorefrontBrandReadModel(
                id=brand.id,
                name=brand.name,
                slug=brand.slug,
                logo_url=brand.logo_url,
            )

        # Supplier — only ``type`` is exposed to the storefront.
        supplier_model = None
        if supplier is not None:
            supplier_model = StorefrontSupplierReadModel(
                type=getattr(supplier.type, "value", str(supplier.type)),
            )

        # Price
        price_model = None
        if min_price is not None:
            price_model = StorefrontMoneyReadModel(
                amount=min_price,
                currency="RUB",
                compare_at=compare_at,
            )

        return StorefrontProductDetailReadModel(
            id=product.id,
            slug=product.slug,
            title_i18n=product.title_i18n or {},
            description_i18n=product.description_i18n or {},
            brand=brand_model,
            supplier=supplier_model,
            price=price_model,
            popularity_score=product.popularity_score or 0,
            published_at=product.published_at,
            variant_count=total_variant_count,
            in_stock=has_stock,
            primary_category_id=product.primary_category_id,
            media=media_models,
            variants=variant_models,
            attributes=attr_models,
            variant_options=variant_options,
            breadcrumbs=breadcrumbs,
            tags=product.tags or [],
            version=product.version,
        )
