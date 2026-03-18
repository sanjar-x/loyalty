"""
Command handler: bulk reorder category-attribute bindings.
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.domain.exceptions import CategoryNotFoundError
from src.modules.catalog.domain.interfaces import (
    ICategoryAttributeBindingRepository,
    ICategoryRepository,
)
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
    ):
        self._category_repo = category_repo
        self._binding_repo = binding_repo
        self._uow = uow

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

            updates = [(item.binding_id, item.sort_order) for item in command.items]
            await self._binding_repo.bulk_update_sort_order(updates)
            await self._uow.commit()
