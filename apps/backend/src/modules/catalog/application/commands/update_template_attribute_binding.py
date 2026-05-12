"""
Command handler: update a template-attribute binding.

Loads the binding, validates ownership, applies partial updates to mutable
fields, emits an update event, and cascades effective-attribute cache
invalidation to the template and all its descendants.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.application.queries.resolve_template_attributes import (
    invalidate_template_effective_cache,
)
from src.modules.catalog.domain.events import TemplateAttributeBindingUpdatedEvent
from src.modules.catalog.domain.exceptions import (
    TemplateAttributeBindingNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeTemplateRepository,
    ITemplateAttributeBindingRepository,
)
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateTemplateAttributeBindingResult:
    """Output after successfully updating a template-attribute binding."""

    id: uuid.UUID
    template_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int
    requirement_level: str
    filter_settings: dict[str, Any] | None


@dataclass(frozen=True)
class UpdateTemplateAttributeBindingCommand:
    """Input for updating a template-attribute binding.

    Attributes:
        binding_id: UUID of the binding to update.
        template_id: UUID of the template that owns the binding (ownership guard).
        sort_order: New display ordering, or None to keep current.
        requirement_level: New requirement level, or None to keep current.
        filter_settings: New filter settings, or None to keep current.
        _provided_fields: Set of field names explicitly provided by the caller.
    """

    binding_id: uuid.UUID
    template_id: uuid.UUID
    sort_order: int | None = None
    requirement_level: RequirementLevel | None = None
    filter_settings: dict[str, Any] | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


class UpdateTemplateAttributeBindingHandler:
    """Apply partial updates to a template-attribute binding.

    Attributes:
        _template_repo: AttributeTemplate repository port.
        _binding_repo: TemplateAttributeBinding repository port.
        _uow: Unit of Work for transactional writes.
        _cache: Cache service for effective attribute cache invalidation.
        _logger: Structured logger with handler context.
    """

    def __init__(
        self,
        template_repo: IAttributeTemplateRepository,
        binding_repo: ITemplateAttributeBindingRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._template_repo = template_repo
        self._binding_repo = binding_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="UpdateTemplateAttributeBindingHandler")

    async def handle(
        self, command: UpdateTemplateAttributeBindingCommand
    ) -> UpdateTemplateAttributeBindingResult:
        """Execute the update-template-attribute-binding command.

        Args:
            command: Binding update parameters.

        Returns:
            Full updated binding data.

        Raises:
            TemplateAttributeBindingNotFoundError: If the binding does not exist
                or does not belong to the specified template.
        """
        async with self._uow:
            binding = await self._binding_repo.get(command.binding_id)
            if binding is None or binding.template_id != command.template_id:
                raise TemplateAttributeBindingNotFoundError(
                    binding_id=command.binding_id
                )

            _SAFE_FIELDS = frozenset(
                {
                    "sort_order",
                    "requirement_level",
                    "filter_settings",
                }
            )
            safe_fields = command._provided_fields & _SAFE_FIELDS
            update_kwargs: dict[str, Any] = {
                f: getattr(command, f) for f in safe_fields
            }

            if update_kwargs:
                binding.update(**update_kwargs)

            binding.add_domain_event(
                TemplateAttributeBindingUpdatedEvent(
                    binding_id=binding.id,
                    aggregate_id=str(binding.id),
                )
            )

            await self._binding_repo.update(binding)
            self._uow.register_aggregate(binding)
            await self._uow.commit()

            result = UpdateTemplateAttributeBindingResult(
                id=binding.id,
                template_id=binding.template_id,
                attribute_id=binding.attribute_id,
                sort_order=binding.sort_order,
                requirement_level=binding.requirement_level.value,
                filter_settings=dict(binding.filter_settings)
                if binding.filter_settings
                else None,
            )

        try:
            await invalidate_template_effective_cache(
                self._cache, self._template_repo, command.template_id
            )
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))

        return result
