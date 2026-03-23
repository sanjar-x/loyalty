"""
Command handler: update a category-attribute binding.

Applies partial updates to sort_order, requirement_level, flag_overrides,
and filter_settings. Emits ``CategoryAttributeBindingUpdatedEvent``.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from src.modules.catalog.application.constants import storefront_cache_key
from src.modules.catalog.domain.events import CategoryAttributeBindingUpdatedEvent
from src.modules.catalog.domain.exceptions import (
    CategoryAttributeBindingNotFoundError,
)
from src.modules.catalog.domain.interfaces import ICategoryAttributeBindingRepository
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.uow import IUnitOfWork


_SENTINEL: object = object()


@dataclass(frozen=True)
class UpdateCategoryAttributeBindingCommand:
    """Input for updating a binding. category_id/attribute_id are immutable."""

    binding_id: uuid.UUID
    category_id: uuid.UUID
    sort_order: int | None = None
    requirement_level: RequirementLevel | None = None
    flag_overrides: dict[str, Any] | None = _SENTINEL  # type: ignore[assignment]
    filter_settings: dict[str, Any] | None = _SENTINEL  # type: ignore[assignment]


@dataclass(frozen=True)
class UpdateCategoryAttributeBindingResult:
    """Output of the update-category-attribute-binding command."""

    id: uuid.UUID
    category_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int
    requirement_level: str
    flag_overrides: dict[str, Any] | None
    filter_settings: dict[str, Any] | None


class UpdateCategoryAttributeBindingHandler:
    """Apply partial updates to an existing category-attribute binding."""

    def __init__(
        self,
        binding_repo: ICategoryAttributeBindingRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
    ):
        self._binding_repo = binding_repo
        self._uow = uow
        self._cache = cache

    async def handle(
        self, command: UpdateCategoryAttributeBindingCommand
    ) -> UpdateCategoryAttributeBindingResult:
        """Execute the update-binding command.

        Returns:
            Rich result containing the updated binding fields.

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

            update_kwargs: dict[str, Any] = dict(
                sort_order=command.sort_order,
                requirement_level=command.requirement_level,
            )
            if command.flag_overrides is not _SENTINEL:
                update_kwargs["flag_overrides"] = command.flag_overrides
            if command.filter_settings is not _SENTINEL:
                update_kwargs["filter_settings"] = command.filter_settings

            binding.update(**update_kwargs)

            binding.add_domain_event(
                CategoryAttributeBindingUpdatedEvent(
                    binding_id=binding.id,
                    aggregate_id=str(binding.id),
                )
            )

            await self._binding_repo.update(binding)
            self._uow.register_aggregate(binding)
            await self._uow.commit()

        # Invalidate storefront cache for the affected category
        await self._cache.delete(storefront_cache_key(command.category_id))

        return UpdateCategoryAttributeBindingResult(
            id=binding.id,
            category_id=binding.category_id,
            attribute_id=binding.attribute_id,
            sort_order=binding.sort_order,
            requirement_level=binding.requirement_level.value,
            flag_overrides=dict(binding.flag_overrides) if binding.flag_overrides else None,
            filter_settings=dict(binding.filter_settings) if binding.filter_settings else None,
        )
