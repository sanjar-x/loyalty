"""
Command handler: unbind an attribute from a family.

Loads the binding, validates ownership, emits a deletion event, removes
the binding, and cascades effective-attribute cache invalidation to
the family and all its descendants.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.queries.resolve_family_attributes import (
    invalidate_family_effective_cache,
)
from src.modules.catalog.domain.events import FamilyAttributeBindingDeletedEvent
from src.modules.catalog.domain.exceptions import (
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
class UnbindAttributeFromFamilyCommand:
    """Input for unbinding an attribute from a family.

    Attributes:
        binding_id: UUID of the binding to remove.
        family_id: UUID of the family that owns the binding (ownership guard).
    """

    binding_id: uuid.UUID
    family_id: uuid.UUID


class UnbindAttributeFromFamilyHandler:
    """Remove a family-attribute binding with ownership validation.

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
        self._logger = logger.bind(handler="UnbindAttributeFromFamilyHandler")

    async def handle(self, command: UnbindAttributeFromFamilyCommand) -> None:
        """Execute the unbind-attribute-from-family command.

        Args:
            command: Unbinding parameters.

        Raises:
            FamilyAttributeBindingNotFoundError: If the binding does not exist
                or does not belong to the specified family.
        """
        async with self._uow:
            binding = await self._binding_repo.get(command.binding_id)
            if binding is None or binding.family_id != command.family_id:
                raise FamilyAttributeBindingNotFoundError(
                    binding_id=command.binding_id
                )

            binding.add_domain_event(
                FamilyAttributeBindingDeletedEvent(
                    binding_id=binding.id,
                    family_id=binding.family_id,
                    attribute_id=binding.attribute_id,
                    aggregate_id=str(binding.id),
                )
            )

            self._uow.register_aggregate(binding)
            await self._binding_repo.delete(command.binding_id)
            await self._uow.commit()

        try:
            await invalidate_family_effective_cache(
                self._cache, self._family_repo, command.family_id
            )
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))
