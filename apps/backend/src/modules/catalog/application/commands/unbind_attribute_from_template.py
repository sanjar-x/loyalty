"""
Command handler: unbind an attribute from a template.

Loads the binding, validates ownership, emits a deletion event, removes
the binding, and cascades effective-attribute cache invalidation to
the template and all its descendants.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.queries.resolve_template_attributes import (
    invalidate_template_effective_cache,
)
from src.modules.catalog.domain.events import TemplateAttributeBindingDeletedEvent
from src.modules.catalog.domain.exceptions import (
    TemplateAttributeBindingNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeTemplateRepository,
    ITemplateAttributeBindingRepository,
)
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UnbindAttributeFromTemplateCommand:
    """Input for unbinding an attribute from a template.

    Attributes:
        binding_id: UUID of the binding to remove.
        template_id: UUID of the template that owns the binding (ownership guard).
    """

    binding_id: uuid.UUID
    template_id: uuid.UUID


class UnbindAttributeFromTemplateHandler:
    """Remove a template-attribute binding with ownership validation.

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
        self._logger = logger.bind(handler="UnbindAttributeFromTemplateHandler")

    async def handle(self, command: UnbindAttributeFromTemplateCommand) -> None:
        """Execute the unbind-attribute-from-template command.

        Args:
            command: Unbinding parameters.

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

            binding.add_domain_event(
                TemplateAttributeBindingDeletedEvent(
                    binding_id=binding.id,
                    template_id=binding.template_id,
                    attribute_id=binding.attribute_id,
                    aggregate_id=str(binding.id),
                )
            )

            self._uow.register_aggregate(binding)
            await self._binding_repo.delete(command.binding_id)
            await self._uow.commit()

        try:
            await invalidate_template_effective_cache(
                self._cache, self._template_repo, command.template_id
            )
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))
