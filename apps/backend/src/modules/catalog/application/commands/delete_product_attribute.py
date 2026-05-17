"""
Command handler: delete an attribute assignment from a product.

Looks up the ``ProductAttributeValue`` by the product+attribute pair
and deletes it. Raises ``ProductAttributeValueNotFoundError`` if no
such assignment exists. Mirrors ``AssignProductAttributeHandler``'s
post-commit cache invalidation so PDP and facet aggregations refresh
after a removed value just as they do after a new value (otherwise a
filterable attribute removed from a product stays in the cached facet
counts until the next mutation or daily roll).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import (
    STOREFRONT_FACET_GENERATION_KEY,
    storefront_pdp_cache_key,
)
from src.modules.catalog.domain.exceptions import (
    ProductAttributeValueNotFoundError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IProductAttributeValueRepository,
    IProductRepository,
)
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteProductAttributeCommand:
    """Input for deleting an attribute assignment from a product.

    Attributes:
        product_id: UUID of the target Product aggregate.
        attribute_id: UUID of the Attribute to un-assign.
    """

    product_id: uuid.UUID
    attribute_id: uuid.UUID


class DeleteProductAttributeHandler:
    """Delete an attribute assignment from a product."""

    def __init__(
        self,
        product_repo: IProductRepository,
        pav_repo: IProductAttributeValueRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._pav_repo = pav_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="DeleteProductAttributeHandler")

    async def handle(self, command: DeleteProductAttributeCommand) -> None:
        """Execute the delete-product-attribute command.

        Args:
            command: Product attribute deletion parameters.

        Raises:
            ProductNotFoundError: If the product cannot be loaded (needed
                for its ``slug`` to invalidate the PDP cache key).
            ProductAttributeValueNotFoundError: If the product does not
                have this attribute assigned.
        """
        async with self._uow:
            product = await self._product_repo.get(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

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

        # Symmetric with ``AssignProductAttributeHandler``: PDP cache
        # for this product is now stale, and the global facet
        # generation counter participates in PLP/search query keys.
        try:
            await self._cache.delete(storefront_pdp_cache_key(product.slug))
            await self._cache.increment(STOREFRONT_FACET_GENERATION_KEY)
        except Exception as exc:  # pragma: no cover
            self._logger.warning("pdp_cache_invalidation_failed", error=str(exc))

        self._logger.info(
            "Product attribute deleted",
            product_id=str(command.product_id),
            attribute_id=str(command.attribute_id),
        )
