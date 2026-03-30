"""Command handler: soft-delete a product variant.

Fetches the product aggregate with its variants, delegates the
soft-delete to ``Product.remove_variant()``, persists the change,
and commits via UoW. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.interfaces import IProductRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteVariantCommand:
    """Input for soft-deleting a product variant.

    Attributes:
        product_id: UUID of the product that owns the variant.
        variant_id: UUID of the variant to soft-delete.
    """

    product_id: uuid.UUID
    variant_id: uuid.UUID


class DeleteVariantHandler:
    """Soft-delete a product variant within a product aggregate.

    Raises LastVariantRemovalError (from the domain) if this is the
    last active variant on the product.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteVariantHandler")

    async def handle(self, command: DeleteVariantCommand) -> None:
        """Execute the delete-variant command.

        Fetches the product with eagerly loaded variants, delegates
        soft-deletion to the domain aggregate, persists and commits.

        Args:
            command: Variant deletion parameters.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
            VariantNotFoundError: If no active variant with the given ID
                exists within the product (raised by ``Product.remove_variant``).
            LastVariantRemovalError: If this is the last active variant
                (raised by ``Product.remove_variant``).
        """
        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(
                command.product_id
            )
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            product.remove_variant(command.variant_id)

            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()
