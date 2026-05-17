"""
Command handler: soft-delete a SKU variant from a product.

Fetches the product aggregate with its SKUs, delegates the soft-delete
to ``Product.remove_sku()``, persists the change, and commits via UoW.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import storefront_pdp_cache_key
from src.modules.catalog.domain.exceptions import (
    ProductNotFoundError,
    SKUNotFoundError,
)
from src.modules.catalog.domain.interfaces import IProductRepository
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteSKUCommand:
    """Input for soft-deleting a SKU variant.

    Attributes:
        product_id: UUID of the product that owns the SKU.
        variant_id: UUID of the variant the SKU is expected to belong to.
            The handler enforces this against the loaded aggregate so a
            ``DELETE /products/A/variants/X/skus/{sku-of-Y}`` cannot
            silently delete a SKU from a sibling variant.
        sku_id: UUID of the SKU to soft-delete.
    """

    product_id: uuid.UUID
    variant_id: uuid.UUID
    sku_id: uuid.UUID


class DeleteSKUHandler:
    """Soft-delete a SKU variant within a product aggregate."""

    def __init__(
        self,
        product_repo: IProductRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="DeleteSKUHandler")

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
            product = await self._product_repo.get_for_update_with_variants(
                command.product_id
            )
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            # ``find_sku`` walks every variant, so the URL's ``variantId``
            # would otherwise be cosmetic — a request for variant X could
            # delete a SKU owned by variant Y. Reject the cross-variant
            # routing with a clean 404 instead of silently mutating.
            sku = product.find_sku(command.sku_id)
            if sku is None or sku.variant_id != command.variant_id:
                raise SKUNotFoundError(sku_id=command.sku_id)

            product.remove_sku(command.sku_id)

            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        try:
            await self._cache.delete(storefront_pdp_cache_key(product.slug))
        except Exception as exc:  # pragma: no cover
            self._logger.warning("pdp_cache_invalidation_failed", error=str(exc))
