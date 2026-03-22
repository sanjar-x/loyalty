"""
Command handler: assign an attribute value to a product.

Validates that the product exists and that the attribute is not already
assigned, then creates a ``ProductAttributeValue`` record linking the
product to the chosen dictionary value. Domain events for product
attribute assignments are deferred to a future phase.
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import ProductAttributeValue
from src.modules.catalog.domain.exceptions import (
    AttributeNotFoundError,
    AttributeValueNotFoundError,
    DuplicateProductAttributeError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeValueRepository,
    IProductAttributeValueRepository,
    IProductRepository,
)
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AssignProductAttributeCommand:
    """Input for assigning an attribute value to a product.

    Attributes:
        product_id: UUID of the target Product aggregate.
        attribute_id: UUID of the Attribute being assigned.
        attribute_value_id: UUID of the chosen AttributeValue.
    """

    product_id: uuid.UUID
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID


@dataclass(frozen=True)
class AssignProductAttributeResult:
    """Output of product attribute assignment.

    Attributes:
        pav_id: UUID of the newly created ProductAttributeValue.
    """

    pav_id: uuid.UUID


class AssignProductAttributeHandler:
    """Assign an attribute value to a product with duplicate guard.

    Verifies that the product exists and that the same attribute is not
    already assigned before creating the ``ProductAttributeValue`` record.
    Domain events are deferred to a future phase.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        pav_repo: IProductAttributeValueRepository,
        attribute_repo: IAttributeRepository,
        attribute_value_repo: IAttributeValueRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._product_repo = product_repo
        self._pav_repo = pav_repo
        self._attribute_repo = attribute_repo
        self._attribute_value_repo = attribute_value_repo
        self._uow = uow

    async def handle(self, command: AssignProductAttributeCommand) -> AssignProductAttributeResult:
        """Execute the assign-product-attribute command.

        Args:
            command: Product attribute assignment parameters.

        Returns:
            Result containing the new ProductAttributeValue UUID.

        Raises:
            ProductNotFoundError: If the product does not exist.
            DuplicateProductAttributeError: If the attribute is already
                assigned to this product.
        """
        async with self._uow:
            product = await self._product_repo.get(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            # --- Validate attribute exists ---
            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            # --- Validate attribute value exists and belongs to the attribute ---
            attr_value = await self._attribute_value_repo.get(command.attribute_value_id)
            if attr_value is None:
                raise AttributeValueNotFoundError(value_id=command.attribute_value_id)
            if attr_value.attribute_id != command.attribute_id:
                raise AttributeValueNotFoundError(value_id=command.attribute_value_id)

            if await self._pav_repo.exists(command.product_id, command.attribute_id):
                raise DuplicateProductAttributeError(
                    product_id=command.product_id,
                    attribute_id=command.attribute_id,
                )

            pav = ProductAttributeValue.create(
                product_id=command.product_id,
                attribute_id=command.attribute_id,
                attribute_value_id=command.attribute_value_id,
            )

            await self._pav_repo.add(pav)
            await self._uow.commit()

        return AssignProductAttributeResult(pav_id=pav.id)
