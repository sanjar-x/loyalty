"""
Command handler: delete a category.

Verifies the category exists and has no children before removing it.
Invalidates the category tree cache on success. Part of the
application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import CATEGORY_TREE_CACHE_KEY
from src.modules.catalog.domain.events import CategoryDeletedEvent
from src.modules.catalog.domain.exceptions import (
    CategoryHasChildrenError,
    CategoryHasProductsError,
    CategoryNotFoundError,
)
from src.modules.catalog.domain.interfaces import ICategoryRepository
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteCategoryCommand:
    """Input for deleting a category.

    Attributes:
        category_id: UUID of the category to delete.
    """

    category_id: uuid.UUID


class DeleteCategoryHandler:
    """Delete a leaf category (one with no children).

    Attributes:
        _category_repo: Category repository port.
        _uow: Unit of Work for transactional writes.
        _cache: Cache service for tree cache invalidation.
        _logger: Structured logger with handler context.
    """

    def __init__(
        self,
        category_repo: ICategoryRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ):
        self._category_repo = category_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="DeleteCategoryHandler")

    async def handle(self, command: DeleteCategoryCommand) -> None:
        """Execute the delete-category command.

        Args:
            command: Category deletion parameters.

        Raises:
            CategoryNotFoundError: If the category does not exist.
            CategoryHasChildrenError: If the category still has children.
            CategoryHasProductsError: If the category still has associated products.
        """
        async with self._uow:
            category = await self._category_repo.get_for_update(command.category_id)
            if category is None:
                raise CategoryNotFoundError(category_id=command.category_id)

            has_children = await self._category_repo.has_children(command.category_id)
            if has_children:
                raise CategoryHasChildrenError(category_id=command.category_id)

            has_products = await self._category_repo.has_products(command.category_id)
            if has_products:
                raise CategoryHasProductsError(category_id=command.category_id)

            category.add_domain_event(
                CategoryDeletedEvent(
                    category_id=category.id,
                    slug=category.slug,
                    aggregate_id=str(category.id),
                )
            )
            self._uow.register_aggregate(category)
            await self._category_repo.delete(command.category_id)
            await self._uow.commit()

        try:
            await self._cache.delete(CATEGORY_TREE_CACHE_KEY)
        except Exception as e:
            self._logger.warning(
                "Failed to invalidate category tree cache", error=str(e)
            )

        self._logger.info("Category deleted", category_id=str(command.category_id))
