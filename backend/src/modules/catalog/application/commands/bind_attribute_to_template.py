"""
Command handler: bind an attribute to a template.

Validates that both the template and attribute exist, checks for duplicate
bindings, creates a new TemplateAttributeBinding, and cascades effective-
attribute cache invalidation to the template and all its descendants.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass
from typing import Any

from src.modules.catalog.application.constants import (
    storefront_card_cache_key,
    storefront_comparison_cache_key,
    storefront_filters_cache_key,
    storefront_form_cache_key,
    template_effective_attrs_cache_key,
)
from src.modules.catalog.domain.entities import TemplateAttributeBinding
from src.modules.catalog.domain.events import TemplateAttributeBindingCreatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeNotFoundError,
    AttributeTemplateNotFoundError,
    TemplateAttributeBindingAlreadyExistsError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeTemplateRepository,
    ITemplateAttributeBindingRepository,
)
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class BindAttributeToTemplateCommand:
    """Input for binding an attribute to a template.

    Attributes:
        template_id: UUID of the target attribute template.
        attribute_id: UUID of the attribute to bind.
        sort_order: Display ordering of the attribute within the template.
        requirement_level: Required / recommended / optional.
        filter_settings: Optional per-template filter configuration.
    """

    template_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int = 0
    requirement_level: RequirementLevel = RequirementLevel.OPTIONAL
    filter_settings: dict[str, Any] | None = None


@dataclass(frozen=True)
class BindAttributeToTemplateResult:
    """Output of attribute-to-template binding.

    Attributes:
        binding_id: UUID of the newly created binding.
        affected_categories_count: Number of categories affected by this binding.
    """

    binding_id: uuid.UUID
    affected_categories_count: int = 0


class BindAttributeToTemplateHandler:
    """Bind an attribute to a template with duplicate and existence checks.

    Attributes:
        _template_repo: AttributeTemplate repository port.
        _attribute_repo: Attribute repository port.
        _binding_repo: TemplateAttributeBinding repository port.
        _uow: Unit of Work for transactional writes.
        _cache: Cache service for effective attribute cache invalidation.
        _logger: Structured logger with handler context.
    """

    def __init__(
        self,
        template_repo: IAttributeTemplateRepository,
        attribute_repo: IAttributeRepository,
        binding_repo: ITemplateAttributeBindingRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._template_repo = template_repo
        self._attribute_repo = attribute_repo
        self._binding_repo = binding_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="BindAttributeToTemplateHandler")

    async def handle(
        self, command: BindAttributeToTemplateCommand
    ) -> BindAttributeToTemplateResult:
        """Execute the bind-attribute-to-template command.

        Args:
            command: Binding creation parameters.

        Returns:
            Result containing the new binding's ID.

        Raises:
            AttributeTemplateNotFoundError: If the template does not exist.
            AttributeNotFoundError: If the attribute does not exist.
            TemplateAttributeBindingAlreadyExistsError: If the pair is already bound.
        """
        async with self._uow:
            template = await self._template_repo.get(command.template_id)
            if template is None:
                raise AttributeTemplateNotFoundError(template_id=command.template_id)

            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            if await self._binding_repo.check_binding_exists(
                template_id=command.template_id,
                attribute_id=command.attribute_id,
            ):
                raise TemplateAttributeBindingAlreadyExistsError(
                    template_id=command.template_id,
                    attribute_id=command.attribute_id,
                )

            binding = TemplateAttributeBinding.create(
                template_id=command.template_id,
                attribute_id=command.attribute_id,
                sort_order=command.sort_order,
                requirement_level=command.requirement_level,
                filter_settings=command.filter_settings,
            )

            binding.add_domain_event(
                TemplateAttributeBindingCreatedEvent(
                    binding_id=binding.id,
                    template_id=command.template_id,
                    attribute_id=command.attribute_id,
                    aggregate_id=str(binding.id),
                )
            )

            binding = await self._binding_repo.add(binding)
            self._uow.register_aggregate(binding)

            # Pre-collect data for post-commit cache invalidation
            affected_category_ids = (
                await self._template_repo.get_category_ids_by_template_ids(
                    [command.template_id]
                )
            )

            await self._uow.commit()

        # Cache invalidation after commit using pre-collected IDs
        try:
            keys = [template_effective_attrs_cache_key(command.template_id)]
            for cat_id in affected_category_ids:
                keys.append(storefront_filters_cache_key(cat_id))
                keys.append(storefront_card_cache_key(cat_id))
                keys.append(storefront_comparison_cache_key(cat_id))
                keys.append(storefront_form_cache_key(cat_id))
            if keys:
                await self._cache.delete_many(keys)
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))

        return BindAttributeToTemplateResult(
            binding_id=binding.id,
            affected_categories_count=len(affected_category_ids),
        )
