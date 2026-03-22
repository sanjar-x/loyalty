"""
Query handler: list SKUs for a given product.

Strict CQRS read side -- queries the ORM directly and returns
a list of SKUReadModel DTOs for a specific product.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.catalog.application.queries.read_models import (
    MoneyReadModel,
    SKUReadModel,
    VariantAttributePairReadModel,
)
from src.modules.catalog.infrastructure.models import (
    SKU as OrmSKU,
)


def sku_orm_to_read_model(orm: OrmSKU) -> SKUReadModel:
    """Convert an ORM SKU row to a SKUReadModel."""
    variant_attrs = [
        VariantAttributePairReadModel(
            attribute_id=link.attribute_id,
            attribute_value_id=link.attribute_value_id,
        )
        for link in orm.attribute_values
    ]

    compare_at: MoneyReadModel | None = None
    if orm.compare_at_price is not None:
        compare_at = MoneyReadModel(
            amount=orm.compare_at_price,
            currency=orm.currency,
        )

    sku_price: MoneyReadModel | None = None
    if orm.price is not None:
        sku_price = MoneyReadModel(amount=orm.price, currency=orm.currency)

    return SKUReadModel(
        id=orm.id,
        product_id=orm.product_id,
        variant_id=orm.variant_id,
        sku_code=orm.sku_code,
        variant_hash=orm.variant_hash,
        price=sku_price,
        resolved_price=sku_price,
        compare_at_price=compare_at,
        is_active=orm.is_active,
        version=orm.version,
        deleted_at=orm.deleted_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        variant_attributes=variant_attrs,
    )


@dataclass(frozen=True)
class ListSKUsQuery:
    """Parameters for listing SKUs of a product.

    Attributes:
        product_id: UUID of the parent product.
    """

    product_id: uuid.UUID


class ListSKUsHandler:
    """Fetch all SKUs for a given product."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListSKUsQuery) -> list[SKUReadModel]:
        """Retrieve all SKUs for a product, ordered by creation time.

        Eagerly loads variant attribute links for each SKU.

        Args:
            query: Query parameters with the parent product_id.

        Returns:
            List of SKU read models.
        """
        stmt = (
            select(OrmSKU)
            .where(OrmSKU.product_id == query.product_id)
            .options(selectinload(OrmSKU.attribute_values))
            .order_by(OrmSKU.created_at)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [sku_orm_to_read_model(orm) for orm in rows]
