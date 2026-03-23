"""
Command handler: unbind an attribute from a category.

Removes the binding and emits ``CategoryAttributeBindingDeletedEvent``.
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import storefront_cache_key
from src.modules.catalog.domain.events import CategoryAttributeBindingDeletedEvent
from src.modules.catalog.domain.exceptions import (
    CategoryAttributeBindingNotFoundError,
)
from src.modules.catalog.domain.interfaces import ICategoryAttributeBindingRepository
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UnbindAttributeFromCategoryCommand:
    """Input for unbinding an attribute from a category."""

    binding_id: uuid.UUID
    category_id: uuid.UUID


class UnbindAttributeFromCategoryHandler:
    """Remove a category-attribute binding."""

    def __init__(
        self,
        binding_repo: ICategoryAttributeBindingRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
    ):
        self._binding_repo = binding_repo
        self._uow = uow
        self._cache = cache

    async def handle(self, command: UnbindAttributeFromCategoryCommand) -> None:
        """Execute the unbind command.

        Raises:
            CategoryAttributeBindingNotFoundError: If the binding does not exist
                or does not belong to the specified category.
        """
        async with self._uow:
            binding = await self._binding_repo.get(command.binding_id)
            if binding is None:
                raise CategoryAttributeBindingNotFoundError(binding_id=command.binding_id)

            if binding.category_id != command.category_id:
                raise CategoryAttributeBindingNotFoundError(binding_id=command.binding_id)

            binding.add_domain_event(
                CategoryAttributeBindingDeletedEvent(
                    category_id=binding.category_id,
                    attribute_id=binding.attribute_id,
                    binding_id=binding.id,
                    aggregate_id=str(binding.id),
                )
            )

            self._uow.register_aggregate(binding)
            await self._binding_repo.delete(command.binding_id)
            await self._uow.commit()

        # Invalidate storefront cache for the affected category
        await self._cache.delete(storefront_cache_key(command.category_id))
