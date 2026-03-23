"""
Command handler: bulk reorder category-attribute bindings.
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.application.queries.storefront import invalidate_storefront_cache
from src.modules.catalog.domain.events import CategoryBindingsReorderedEvent
from src.modules.catalog.domain.exceptions import CategoryNotFoundError
from src.modules.catalog.domain.interfaces import (
    ICategoryAttributeBindingRepository,
    ICategoryRepository,
)
from src.shared.exceptions import ValidationError
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class BindingReorderItem:
    """A single binding reorder instruction."""

    binding_id: uuid.UUID
    sort_order: int


@dataclass(frozen=True)
class ReorderCategoryBindingsCommand:
    """Input for bulk-reordering bindings within a category."""

    category_id: uuid.UUID
    items: list[BindingReorderItem] = field(default_factory=list)


class ReorderCategoryBindingsHandler:
    """Bulk-update sort order for category-attribute bindings atomically."""

    def __init__(
        self,
        category_repo: ICategoryRepository,
        binding_repo: ICategoryAttributeBindingRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ):
        self._category_repo = category_repo
        self._binding_repo = binding_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="ReorderCategoryBindingsHandler")

    async def handle(self, command: ReorderCategoryBindingsCommand) -> None:
        """Execute the reorder-bindings command.

        Raises:
            CategoryNotFoundError: If the category does not exist.
        """
        if not command.items:
            return

        async with self._uow:
            category = await self._category_repo.get(command.category_id)
            if category is None:
                raise CategoryNotFoundError(category_id=command.category_id)

            valid_ids = await self._binding_repo.list_ids_by_category(command.category_id)
            requested_ids = {item.binding_id for item in command.items}
            invalid_ids = requested_ids - valid_ids
            if invalid_ids:
                raise ValidationError(
                    message=f"Binding IDs {invalid_ids} do not belong to category {command.category_id}",
                    details={"invalid_ids": [str(i) for i in invalid_ids]},
                )

            updates = [(item.binding_id, item.sort_order) for item in command.items]
            await self._binding_repo.bulk_update_sort_order(updates)
            category.add_domain_event(
                CategoryBindingsReorderedEvent(
                    category_id=command.category_id,
                    aggregate_id=str(command.category_id),
                )
            )
            self._uow.register_aggregate(category)
            await self._uow.commit()

        # Invalidate storefront cache for the affected category
        try:
            await invalidate_storefront_cache(self._cache, command.category_id)
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))
