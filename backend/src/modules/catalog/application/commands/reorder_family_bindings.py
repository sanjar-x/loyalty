"""
Command handler: reorder family-attribute bindings.

Validates that the family exists, all binding IDs belong to it, then
bulk-updates sort_order and cascades effective-attribute cache
invalidation to the family and all its descendants.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.queries.resolve_family_attributes import (
    invalidate_family_effective_cache,
)
from src.modules.catalog.domain.exceptions import (
    AttributeFamilyNotFoundError,
    FamilyAttributeBindingNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeFamilyRepository,
    IFamilyAttributeBindingRepository,
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
class ReorderFamilyBindingsCommand:
    """Input for reordering family-attribute bindings.

    Attributes:
        family_id: UUID of the family whose bindings are being reordered.
        items: List of reorder instructions.
    """

    family_id: uuid.UUID
    items: list[BindingReorderItem]


class ReorderFamilyBindingsHandler:
    """Bulk-reorder attribute bindings within a family.

    Attributes:
        _family_repo: AttributeFamily repository port.
        _binding_repo: FamilyAttributeBinding repository port.
        _uow: Unit of Work for transactional writes.
        _cache: Cache service for effective attribute cache invalidation.
        _logger: Structured logger with handler context.
    """

    def __init__(
        self,
        family_repo: IAttributeFamilyRepository,
        binding_repo: IFamilyAttributeBindingRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._family_repo = family_repo
        self._binding_repo = binding_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="ReorderFamilyBindingsHandler")

    async def handle(self, command: ReorderFamilyBindingsCommand) -> None:
        """Execute the reorder-family-bindings command.

        Args:
            command: Reorder parameters.

        Raises:
            AttributeFamilyNotFoundError: If the family does not exist.
            FamilyAttributeBindingNotFoundError: If any binding ID does not
                belong to the specified family.
        """
        async with self._uow:
            family = await self._family_repo.get(command.family_id)
            if family is None:
                raise AttributeFamilyNotFoundError(family_id=command.family_id)

            family_binding_ids = await self._binding_repo.list_ids_by_family(
                command.family_id
            )
            requested_ids = {item.binding_id for item in command.items}
            invalid_ids = requested_ids - family_binding_ids
            if invalid_ids:
                raise FamilyAttributeBindingNotFoundError(
                    binding_id=next(iter(invalid_ids))
                )

            updates = [
                (item.binding_id, item.sort_order) for item in command.items
            ]
            await self._binding_repo.bulk_update_sort_order(updates)
            await self._uow.commit()

        try:
            await invalidate_family_effective_cache(
                self._cache, self._family_repo, command.family_id
            )
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))
