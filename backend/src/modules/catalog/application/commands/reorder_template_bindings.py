"""
Command handler: reorder template-attribute bindings.

Validates that the template exists, all binding IDs belong to it, then
bulk-updates sort_order and cascades effective-attribute cache
invalidation to the template and all its descendants.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.queries.resolve_template_attributes import (
    invalidate_template_effective_cache,
)
from src.modules.catalog.domain.exceptions import (
    AttributeTemplateNotFoundError,
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
class BindingReorderItem:
    """A single binding reorder instruction.

    Attributes:
        binding_id: UUID of the binding to reorder.
        sort_order: New display ordering.
    """

    binding_id: uuid.UUID
    sort_order: int


@dataclass(frozen=True)
class ReorderTemplateBindingsCommand:
    """Input for reordering template-attribute bindings.

    Attributes:
        template_id: UUID of the template whose bindings are being reordered.
        items: List of reorder instructions.
    """

    template_id: uuid.UUID
    items: list[BindingReorderItem]


class ReorderTemplateBindingsHandler:
    """Bulk-reorder attribute bindings within a template.

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
        self._logger = logger.bind(handler="ReorderTemplateBindingsHandler")

    async def handle(self, command: ReorderTemplateBindingsCommand) -> None:
        """Execute the reorder-template-bindings command.

        Args:
            command: Reorder parameters.

        Raises:
            AttributeTemplateNotFoundError: If the template does not exist.
            TemplateAttributeBindingNotFoundError: If any binding ID does not
                belong to the specified template.
        """
        async with self._uow:
            template = await self._template_repo.get(command.template_id)
            if template is None:
                raise AttributeTemplateNotFoundError(template_id=command.template_id)

            template_binding_ids = await self._binding_repo.list_ids_by_template(
                command.template_id
            )
            requested_ids = {item.binding_id for item in command.items}
            invalid_ids = requested_ids - template_binding_ids
            if invalid_ids:
                raise TemplateAttributeBindingNotFoundError(
                    binding_id=next(iter(invalid_ids))
                )

            updates = [(item.binding_id, item.sort_order) for item in command.items]
            await self._binding_repo.bulk_update_sort_order(updates)
            await self._uow.commit()

        try:
            await invalidate_template_effective_cache(
                self._cache, self._template_repo, command.template_id
            )
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))
