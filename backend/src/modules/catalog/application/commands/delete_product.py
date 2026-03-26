"""
Command handler: soft-delete a product.

Verifies the product exists, then marks it as soft-deleted via the
``Product.soft_delete()`` domain method. No domain events are emitted
at this stage (deferred to a future MT).
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.interfaces import IProductRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteProductCommand:
    """Input for soft-deleting a product.

    Attributes:
        product_id: UUID of the product to soft-delete.
    """

    product_id: uuid.UUID


class DeleteProductHandler:
    """Soft-delete an existing product by ID."""

    def __init__(
        self,
        product_repo: IProductRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteProductHandler")

    async def handle(self, command: DeleteProductCommand) -> None:
        """Execute the delete-product command.

        Args:
            command: Product deletion parameters.

        Raises:
            ProductNotFoundError: If the product does not exist.
        """
        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            product.soft_delete()
            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()
