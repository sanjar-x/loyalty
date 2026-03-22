"""
Query handler: get a single product by ID.

Strict CQRS read side -- queries the ORM directly via AsyncSession
and returns a ProductReadModel DTO with nested variants, SKUs,
attributes, and computed min/max price aggregations.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.catalog.application.queries.list_variants import variant_orm_to_read_model
from src.modules.catalog.application.queries.read_models import (
    ProductAttributeValueReadModel,
    ProductReadModel,
)
from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.infrastructure.models import (
    ProductVariant as OrmProductVariant,
    SKU as OrmSKU,
)
from src.modules.catalog.infrastructure.models import (
    Product as OrmProduct,
    ProductAttributeValue as OrmProductAttributeValue,
    Attribute as OrmAttribute,
)


class GetProductHandler:
    """Fetch a single product by its UUID with nested variants and attributes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, product_id: uuid.UUID) -> ProductReadModel:
        """Retrieve a product by ID with all nested data.

        Loads variants with their SKUs and variant attribute links eagerly.
        Computes min_price and max_price across active, non-deleted SKUs.

        Args:
            product_id: UUID of the product.

        Returns:
            Full product read model with nested variants and attributes.

        Raises:
            ProductNotFoundError: If the product does not exist.
        """
        stmt = (
            select(OrmProduct)
            .where(
                OrmProduct.id == product_id,
                OrmProduct.deleted_at.is_(None),
            )
            .options(
                selectinload(OrmProduct.variants.and_(OrmProductVariant.deleted_at.is_(None)))
                .selectinload(OrmProductVariant.skus)
                .selectinload(OrmSKU.attribute_values),
                selectinload(OrmProduct.product_attribute_values).selectinload(
                    OrmProductAttributeValue.attribute
                ),
            )
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise ProductNotFoundError(product_id=product_id)

        return self._to_read_model(orm)

    @staticmethod
    def _to_read_model(orm: OrmProduct) -> ProductReadModel:
        """Map an ORM Product to a ProductReadModel with computed prices."""
        variants = [variant_orm_to_read_model(v) for v in orm.variants if v.deleted_at is None]

        # Compute min/max price across active, non-deleted SKUs in all variants
        active_prices: list[int] = []
        for variant in variants:
            for sku in variant.skus:
                if sku.is_active and sku.deleted_at is None and sku.resolved_price is not None:
                    active_prices.append(sku.resolved_price.amount)

        min_price = min(active_prices) if active_prices else None
        max_price = max(active_prices) if active_prices else None

        attributes = [
            ProductAttributeValueReadModel(
                id=pav.id,
                product_id=pav.product_id,
                attribute_id=pav.attribute_id,
                attribute_value_id=pav.attribute_value_id,
                attribute_code=pav.attribute.code if pav.attribute else "",
                attribute_name_i18n=dict(pav.attribute.name_i18n) if pav.attribute else {},
            )
            for pav in orm.product_attribute_values
        ]

        return ProductReadModel(
            id=orm.id,
            slug=orm.slug,
            title_i18n=orm.title_i18n,
            description_i18n=orm.description_i18n,
            status=orm.status.value,
            brand_id=orm.brand_id,
            primary_category_id=orm.primary_category_id,
            supplier_id=orm.supplier_id,
            country_of_origin=orm.country_of_origin,
            tags=list(orm.tags) if orm.tags else [],
            version=orm.version,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            published_at=orm.published_at,
            min_price=min_price,
            max_price=max_price,
            variants=variants,
            attributes=attributes,
        )
