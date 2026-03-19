"""
Command handler: update a category-attribute binding.

Applies partial updates to sort_order, requirement_level, flag_overrides,
and filter_settings. Emits ``CategoryAttributeBindingUpdatedEvent``.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from src.modules.catalog.domain.events import CategoryAttributeBindingUpdatedEvent
from src.modules.catalog.domain.exceptions import (
    CategoryAttributeBindingNotFoundError,
)
from src.modules.catalog.domain.interfaces import ICategoryAttributeBindingRepository
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateCategoryAttributeBindingCommand:
    """Input for updating a binding. category_id/attribute_id are immutable."""

    binding_id: uuid.UUID
    sort_order: int | None = None
    requirement_level: RequirementLevel | None = None
    flag_overrides: dict[str, Any] | None = ...  # type: ignore[assignment]
    filter_settings: dict[str, Any] | None = ...  # type: ignore[assignment]


class UpdateCategoryAttributeBindingHandler:
    """Apply partial updates to an existing category-attribute binding."""

    def __init__(
        self,
        binding_repo: ICategoryAttributeBindingRepository,
        uow: IUnitOfWork,
    ):
        self._binding_repo = binding_repo
        self._uow = uow

    async def handle(self, command: UpdateCategoryAttributeBindingCommand) -> uuid.UUID:
        """Execute the update-binding command.

        Returns:
            UUID of the updated binding.

        Raises:
            CategoryAttributeBindingNotFoundError: If the binding does not exist.
        """
        async with self._uow:
            binding = await self._binding_repo.get(command.binding_id)
            if binding is None:
                raise CategoryAttributeBindingNotFoundError(binding_id=command.binding_id)

            binding.update(
                sort_order=command.sort_order,
                requirement_level=command.requirement_level,
                flag_overrides=command.flag_overrides,
                filter_settings=command.filter_settings,
            )

            binding.add_domain_event(
                CategoryAttributeBindingUpdatedEvent(
                    binding_id=binding.id,
                    aggregate_id=str(binding.id),
                )
            )

            await self._binding_repo.update(binding)
            self._uow.register_aggregate(binding)
            await self._uow.commit()

        return binding.id
