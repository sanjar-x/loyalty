"""
Command handler: bulk update requirement levels for bindings in a category.
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.application.constants import storefront_cache_key
from src.modules.catalog.domain.exceptions import CategoryNotFoundError
from src.modules.catalog.domain.interfaces import (
    ICategoryAttributeBindingRepository,
    ICategoryRepository,
)
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RequirementLevelUpdateItem:
    """A single requirement-level update instruction."""

    binding_id: uuid.UUID
    requirement_level: RequirementLevel


@dataclass(frozen=True)
class BulkUpdateRequirementLevelsCommand:
    """Input for bulk-updating requirement levels within a category."""

    category_id: uuid.UUID
    items: list[RequirementLevelUpdateItem] = field(default_factory=list)


class BulkUpdateRequirementLevelsHandler:
    """Bulk-update requirement levels for bindings atomically."""

    def __init__(
        self,
        category_repo: ICategoryRepository,
        binding_repo: ICategoryAttributeBindingRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
    ):
        self._category_repo = category_repo
        self._binding_repo = binding_repo
        self._uow = uow
        self._cache = cache

    async def handle(self, command: BulkUpdateRequirementLevelsCommand) -> None:
        """Execute the bulk-update-requirement-levels command.

        Raises:
            CategoryNotFoundError: If the category does not exist.
        """
        if not command.items:
            return

        async with self._uow:
            category = await self._category_repo.get(command.category_id)
            if category is None:
                raise CategoryNotFoundError(category_id=command.category_id)

            updates = [(item.binding_id, item.requirement_level.value) for item in command.items]
            await self._binding_repo.bulk_update_requirement_level(updates)
            await self._uow.commit()

        # Invalidate storefront cache for the affected category
        await self._cache.delete(storefront_cache_key(command.category_id))
