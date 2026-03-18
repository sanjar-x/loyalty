"""
Query handler: list product attribute value assignments for a product.

Strict CQRS read side -- queries the product_attribute_values pivot
table directly via AsyncSession and returns ProductAttributeValueReadModel
DTOs.

Note:
    The ProductAttributeValue ORM model is introduced in MT-16. This
    handler will become fully functional once that model is registered.
    Until then, the handler returns an empty list for any product_id.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    ProductAttributeValueReadModel,
)


@dataclass(frozen=True)
class ListProductAttributesQuery:
    """Parameters for listing attribute assignments of a product.

    Attributes:
        product_id: UUID of the product whose attribute values to list.
    """

    product_id: uuid.UUID


class ListProductAttributesHandler:
    """Fetch all attribute value assignments for a given product."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, query: ListProductAttributesQuery
    ) -> list[ProductAttributeValueReadModel]:
        """Retrieve all product attribute value assignments.

        Returns EAV pivot records linking a product to its attribute values.
        The underlying ORM model (ProductAttributeValue) is created in MT-16;
        once available, this handler will query it directly.

        Args:
            query: Query parameters with the product_id.

        Returns:
            List of product attribute value read models.
        """
        # The ProductAttributeValue ORM model does not yet exist (MT-16).
        # Once MT-16 is completed, this handler will be updated to query
        # the product_attribute_values table via:
        #
        #   from src.modules.catalog.infrastructure.models import (
        #       ProductAttributeValue as OrmProductAttributeValue,
        #   )
        #   stmt = (
        #       select(OrmProductAttributeValue)
        #       .where(OrmProductAttributeValue.product_id == query.product_id)
        #       .order_by(OrmProductAttributeValue.attribute_id)
        #   )
        #   result = await self._session.execute(stmt)
        #   rows = result.scalars().all()
        #   return [
        #       ProductAttributeValueReadModel(
        #           id=row.id,
        #           product_id=row.product_id,
        #           attribute_id=row.attribute_id,
        #           attribute_value_id=row.attribute_value_id,
        #       )
        #       for row in rows
        #   ]
        _ = self._session  # used once MT-16 ORM model is available
        _ = query  # used once MT-16 ORM model is available
        return []
