"""
Query handler: list product attribute assignments with attribute metadata.

Joins ProductAttributeValue with Attribute to provide attribute code and name
alongside each assignment. CQRS read side -- queries ORM directly.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    ProductAttributeReadModel,
)
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
)
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValue as OrmProductAttributeValue,
)


class ListProductAttributesQuery:
    """Parameters for listing attribute assignments of a product."""

    def __init__(self, product_id: uuid.UUID) -> None:
        self.product_id = product_id


class ListProductAttributesHandler:
    """Fetch all attribute assignments for a product with attribute metadata."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListProductAttributesQuery) -> list[ProductAttributeReadModel]:
        """Retrieve product attribute assignments joined with attribute data."""
        stmt = (
            select(OrmProductAttributeValue, OrmAttribute)
            .join(OrmAttribute, OrmProductAttributeValue.attribute_id == OrmAttribute.id)
            .where(OrmProductAttributeValue.product_id == query.product_id)
            .order_by(OrmAttribute.code)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            ProductAttributeReadModel(
                id=pav.id,
                product_id=pav.product_id,
                attribute_id=pav.attribute_id,
                attribute_value_id=pav.attribute_value_id,
                attribute_code=attr.code,
                attribute_name_i18n=dict(attr.name_i18n),
            )
            for pav, attr in rows
        ]
