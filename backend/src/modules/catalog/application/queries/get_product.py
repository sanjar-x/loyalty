"""
Query handler: get a single product by ID.

Strict CQRS read side -- queries the ORM directly via AsyncSession
and returns a ProductReadModel DTO with nested SKUs, attributes,
and computed min/max price aggregations.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.catalog.application.queries.read_models import (
    MoneyReadModel,
    ProductAttributeValueReadModel,
    ProductReadModel,
    SKUReadModel,
    VariantAttributePairReadModel,
)
from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.infrastructure.models import (
    SKU as OrmSKU,
)
from src.modules.catalog.infrastructure.models import (
    Product as OrmProduct,
)


class GetProductHandler:
    """Fetch a single product by its UUID with nested SKUs and attributes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, product_id: uuid.UUID) -> ProductReadModel:
        """Retrieve a product by ID with all nested data.

        Loads SKUs with their variant attribute links eagerly. Computes
        min_price and max_price across active, non-deleted SKUs.

        Args:
            product_id: UUID of the product.

        Returns:
            Full product read model with nested SKUs and attributes.

        Raises:
            ProductNotFoundError: If the product does not exist.
        """
        stmt = (
            select(OrmProduct)
            .where(OrmProduct.id == product_id)
            .options(
                selectinload(OrmProduct.skus).selectinload(OrmSKU.attribute_values),
            )
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise ProductNotFoundError(product_id=product_id)

        return self._to_read_model(orm)

    @staticmethod
    def _to_sku_read_model(sku: OrmSKU) -> SKUReadModel:
        """Map an ORM SKU to a SKUReadModel."""
        variant_attrs = [
            VariantAttributePairReadModel(
                attribute_id=link.attribute_id,
                attribute_value_id=link.attribute_value_id,
            )
            for link in sku.attribute_values
        ]

        compare_at: MoneyReadModel | None = None
        if sku.compare_at_price is not None:
            compare_at = MoneyReadModel(
                amount=sku.compare_at_price,
                currency=sku.currency,
            )

        return SKUReadModel(
            id=sku.id,
            product_id=sku.product_id,
            sku_code=sku.sku_code,
            variant_hash=sku.variant_hash,
            price=MoneyReadModel(amount=sku.price, currency=sku.currency),
            compare_at_price=compare_at,
            is_active=sku.is_active,
            version=sku.version,
            deleted_at=sku.deleted_at,
            created_at=sku.created_at,
            updated_at=sku.updated_at,
            variant_attributes=variant_attrs,
        )

    @staticmethod
    def _to_read_model(orm: OrmProduct) -> ProductReadModel:
        """Map an ORM Product to a ProductReadModel with computed prices."""
        skus = [GetProductHandler._to_sku_read_model(s) for s in orm.skus]

        # Compute min/max price across active, non-deleted SKUs
        active_prices = [
            s.price.amount for s in skus if s.is_active and s.deleted_at is None
        ]
        min_price = min(active_prices) if active_prices else None
        max_price = max(active_prices) if active_prices else None

        # Product-level attribute values (EAV pivot records).
        # The ProductAttributeValue ORM model is introduced in MT-16.
        # Until that model and relationship exist, this list remains empty.
        attributes: list[ProductAttributeValueReadModel] = []

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
            skus=skus,
            attributes=attributes,
        )
