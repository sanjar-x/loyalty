"""
Query handler: list product attribute assignments with attribute metadata.

Joins ProductAttributeValue with Attribute to provide attribute code and name
alongside each assignment. CQRS read side -- queries ORM directly.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    ProductAttributeListReadModel,
    ProductAttributeReadModel,
)
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
)
from src.modules.catalog.infrastructure.models import (
    AttributeValue as OrmAttributeValue,
)
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValue as OrmProductAttributeValue,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class ListProductAttributesQuery:
    """Parameters for listing attribute assignments of a product.

    Attributes:
        product_id: UUID of the parent product.
        offset: Number of records to skip.
        limit: Maximum number of records to return.
    """

    product_id: uuid.UUID
    offset: int = 0
    limit: int = 50


class ListProductAttributesHandler:
    """Fetch all attribute assignments for a product with attribute metadata."""

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(handler="ListProductAttributesHandler")

    async def handle(
        self, query: ListProductAttributesQuery
    ) -> ProductAttributeListReadModel:
        """Retrieve paginated product attribute assignments joined with attribute data.

        Args:
            query: Query parameters with product_id and pagination.

        Returns:
            Paginated product attribute list read model.
        """
        count_stmt = (
            select(func.count())
            .select_from(OrmProductAttributeValue)
            .where(OrmProductAttributeValue.product_id == query.product_id)
        )
        count_result = await self._session.execute(count_stmt)
        total: int = count_result.scalar_one()

        stmt = (
            select(OrmProductAttributeValue, OrmAttribute, OrmAttributeValue)
            .join(
                OrmAttribute, OrmProductAttributeValue.attribute_id == OrmAttribute.id
            )
            .join(
                OrmAttributeValue,
                OrmProductAttributeValue.attribute_value_id == OrmAttributeValue.id,
            )
            .where(OrmProductAttributeValue.product_id == query.product_id)
            .order_by(OrmAttribute.code)
            .limit(query.limit)
            .offset(query.offset)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        items = [
            ProductAttributeReadModel(
                id=pav.id,
                product_id=pav.product_id,
                attribute_id=pav.attribute_id,
                attribute_value_id=pav.attribute_value_id,
                attribute_code=attr.code,
                attribute_name_i18n=dict(attr.name_i18n),
                attribute_value_code=attr_val.code,
                attribute_value_name_i18n=dict(attr_val.value_i18n),
            )
            for pav, attr, attr_val in rows
        ]
        return ProductAttributeListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
