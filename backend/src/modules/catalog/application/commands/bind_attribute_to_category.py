"""
Command handler: bind an attribute to a category.

Validates both entities exist and the pair is unique, then persists the
binding and emits ``CategoryAttributeBindingCreatedEvent``.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from src.modules.catalog.application.constants import storefront_cache_key
from src.modules.catalog.domain.entities import CategoryAttributeBinding
from src.modules.catalog.domain.events import CategoryAttributeBindingCreatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeNotFoundError,
    CategoryAttributeBindingAlreadyExistsError,
    CategoryNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    ICategoryAttributeBindingRepository,
    ICategoryRepository,
)
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class BindAttributeToCategoryCommand:
    """Input for binding an attribute to a category."""

    category_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int = 0
    requirement_level: RequirementLevel = RequirementLevel.OPTIONAL
    flag_overrides: dict[str, Any] | None = None
    filter_settings: dict[str, Any] | None = None


@dataclass(frozen=True)
class BindAttributeToCategoryResult:
    """Output of binding creation."""

    binding_id: uuid.UUID


class BindAttributeToCategoryHandler:
    """Bind an attribute to a category with governance settings."""

    def __init__(
        self,
        category_repo: ICategoryRepository,
        attribute_repo: IAttributeRepository,
        binding_repo: ICategoryAttributeBindingRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._category_repo = category_repo
        self._attribute_repo = attribute_repo
        self._binding_repo = binding_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="BindAttributeToCategoryHandler")

    async def handle(
        self, command: BindAttributeToCategoryCommand
    ) -> BindAttributeToCategoryResult:
        """Execute the bind-attribute-to-category command.

        Raises:
            CategoryNotFoundError: If the category does not exist.
            AttributeNotFoundError: If the attribute does not exist.
            CategoryAttributeBindingAlreadyExistsError: If the pair already exists.
        """
        async with self._uow:
            category = await self._category_repo.get(command.category_id)
            if category is None:
                raise CategoryNotFoundError(category_id=command.category_id)

            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            if await self._binding_repo.exists(command.category_id, command.attribute_id):
                raise CategoryAttributeBindingAlreadyExistsError(
                    category_id=command.category_id,
                    attribute_id=command.attribute_id,
                )

            binding = CategoryAttributeBinding.create(
                category_id=command.category_id,
                attribute_id=command.attribute_id,
                sort_order=command.sort_order,
                requirement_level=command.requirement_level,
                flag_overrides=command.flag_overrides,
                filter_settings=command.filter_settings,
            )

            binding.add_domain_event(
                CategoryAttributeBindingCreatedEvent(
                    category_id=command.category_id,
                    attribute_id=command.attribute_id,
                    binding_id=binding.id,
                    aggregate_id=str(binding.id),
                )
            )

            binding = await self._binding_repo.add(binding)
            self._uow.register_aggregate(binding)
            await self._uow.commit()

        # Invalidate storefront cache for the affected category
        await self._cache.delete(storefront_cache_key(command.category_id))

        return BindAttributeToCategoryResult(binding_id=binding.id)
