"""Query handler: list variants for a given product.

Strict CQRS read side -- queries the ORM directly and returns
a list of ProductVariantReadModel DTOs for a specific product.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.catalog.application.queries.list_skus import sku_orm_to_read_model
from src.modules.catalog.application.queries.read_models import (
    MoneyReadModel,
    ProductVariantReadModel,
    SKUReadModel,
)
from src.modules.catalog.infrastructure.models import (
    ProductVariant as OrmProductVariant,
    SKU as OrmSKU,
)


def variant_orm_to_read_model(orm: OrmProductVariant) -> ProductVariantReadModel:
    """Convert an ORM ProductVariant to a read model with nested SKUs."""
    default_price: MoneyReadModel | None = None
    if orm.default_price is not None:
        default_price = MoneyReadModel(amount=orm.default_price, currency=orm.default_currency)

    skus: list[SKUReadModel] = []
    for sku_orm in orm.skus:
        if sku_orm.deleted_at is not None:
            continue
        skus.append(sku_orm_to_read_model(sku_orm, variant_default_price=default_price))

    return ProductVariantReadModel(
        id=orm.id,
        product_id=orm.product_id,
        name_i18n=dict(orm.name_i18n) if orm.name_i18n else {},
        description_i18n=dict(orm.description_i18n) if orm.description_i18n else None,
        sort_order=orm.sort_order,
        default_price=default_price,
        skus=skus,
    )


@dataclass(frozen=True)
class ListVariantsQuery:
    """Parameters for listing variants of a product.

    Attributes:
        product_id: UUID of the parent product.
    """

    product_id: uuid.UUID


class ListVariantsHandler:
    """Fetch all active variants for a given product."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListVariantsQuery) -> list[ProductVariantReadModel]:
        """Retrieve all active variants for a product, ordered by sort_order.

        Eagerly loads SKUs and their variant attribute links for each variant.

        Args:
            query: Query parameters with the parent product_id.

        Returns:
            List of variant read models with nested SKUs.
        """
        stmt = (
            select(OrmProductVariant)
            .where(
                OrmProductVariant.product_id == query.product_id,
                OrmProductVariant.deleted_at.is_(None),
            )
            .options(selectinload(OrmProductVariant.skus).selectinload(OrmSKU.attribute_values))
            .order_by(OrmProductVariant.sort_order)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [variant_orm_to_read_model(orm) for orm in rows]
