"""
Command handler: remove an attribute assignment from a product.

Looks up the ``ProductAttributeValue`` by the product+attribute pair
and deletes it. Raises ``ProductAttributeValueNotFoundError`` if no
such assignment exists. Domain events are deferred to a future phase.
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import ProductAttributeValueNotFoundError
from src.modules.catalog.domain.interfaces import IProductAttributeValueRepository
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RemoveProductAttributeCommand:
    """Input for removing an attribute assignment from a product.

    Attributes:
        product_id: UUID of the target Product aggregate.
        attribute_id: UUID of the Attribute to un-assign.
    """

    product_id: uuid.UUID
    attribute_id: uuid.UUID


class RemoveProductAttributeHandler:
    """Remove an attribute assignment from a product.

    Locates the ``ProductAttributeValue`` record by the product+attribute
    pair and deletes it. Domain events are deferred to a future phase.
    """

    def __init__(
        self,
        pav_repo: IProductAttributeValueRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._pav_repo = pav_repo
        self._uow = uow

    async def handle(self, command: RemoveProductAttributeCommand) -> None:
        """Execute the remove-product-attribute command.

        Args:
            command: Product attribute removal parameters.

        Raises:
            ProductAttributeValueNotFoundError: If the product does not
                have this attribute assigned.
        """
        async with self._uow:
            # Look up the specific PAV record by product+attribute pair.
            target = await self._pav_repo.get_by_product_and_attribute(
                command.product_id, command.attribute_id
            )

            if target is None:
                raise ProductAttributeValueNotFoundError(
                    product_id=command.product_id,
                    attribute_id=command.attribute_id,
                )

            await self._pav_repo.delete(target.id)
            await self._uow.commit()
