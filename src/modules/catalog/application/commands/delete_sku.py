"""
Command handler: soft-delete a SKU variant from a product.

Fetches the product aggregate with its SKUs, delegates the soft-delete
to ``Product.remove_sku()``, persists the change, and commits via UoW.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.interfaces import IProductRepository
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteSKUCommand:
    """Input for soft-deleting a SKU variant.

    Attributes:
        product_id: UUID of the product that owns the SKU.
        sku_id: UUID of the SKU to soft-delete.
    """

    product_id: uuid.UUID
    sku_id: uuid.UUID


class DeleteSKUHandler:
    """Soft-delete a SKU variant within a product aggregate."""

    def __init__(
        self,
        product_repo: IProductRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow

    async def handle(self, command: DeleteSKUCommand) -> None:
        """Execute the delete-SKU command.

        Fetches the product with eagerly loaded SKUs, delegates
        soft-deletion to the domain aggregate, persists and commits.

        Args:
            command: SKU deletion parameters.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
            SKUNotFoundError: If no active SKU with the given ID exists
                within the product (raised by ``Product.remove_sku``).
        """
        async with self._uow:
            product = await self._product_repo.get_with_skus(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            product.remove_sku(command.sku_id)

            await self._product_repo.update(product)
            await self._uow.commit()
