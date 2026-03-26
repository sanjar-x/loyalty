"""
Command handler: remove a family attribute exclusion.

Validates the exclusion exists and belongs to the specified family, then
deletes it and invalidates effective-attribute caches for the family and
all its descendants.

Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.queries.resolve_family_attributes import (
    invalidate_family_effective_cache,
)
from src.modules.catalog.domain.events import FamilyAttributeExclusionRemovedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeFamilyNotFoundError,
    FamilyAttributeExclusionNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeFamilyRepository,
    IFamilyAttributeExclusionRepository,
)
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RemoveFamilyExclusionCommand:
    """Input for removing a family attribute exclusion.

    Attributes:
        exclusion_id: UUID of the exclusion to remove.
        family_id: UUID of the family that owns the exclusion.
    """

    exclusion_id: uuid.UUID
    family_id: uuid.UUID


class RemoveFamilyExclusionHandler:
    """Remove an attribute exclusion from a family.

    Validates ownership before deletion and invalidates effective-attribute
    caches for the family and all its descendants.
    """

    def __init__(
        self,
        family_repo: IAttributeFamilyRepository,
        exclusion_repo: IFamilyAttributeExclusionRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._family_repo = family_repo
        self._exclusion_repo = exclusion_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="RemoveFamilyExclusionHandler")

    async def handle(self, command: RemoveFamilyExclusionCommand) -> None:
        """Execute the remove-family-exclusion command.

        Args:
            command: Exclusion removal parameters.

        Raises:
            FamilyAttributeExclusionNotFoundError: If the exclusion does
                not exist.
            AttributeFamilyNotFoundError: If the exclusion does not belong
                to the specified family.
        """
        async with self._uow:
            # 1. Load exclusion, validate exists
            exclusion = await self._exclusion_repo.get(command.exclusion_id)
            if exclusion is None:
                raise FamilyAttributeExclusionNotFoundError(
                    exclusion_id=command.exclusion_id
                )

            # 2. Verify exclusion belongs to the specified family
            if exclusion.family_id != command.family_id:
                raise FamilyAttributeExclusionNotFoundError(
                    exclusion_id=command.exclusion_id
                )

            # 3. Emit domain event
            exclusion.add_domain_event(
                FamilyAttributeExclusionRemovedEvent(
                    exclusion_id=exclusion.id,
                    family_id=exclusion.family_id,
                    attribute_id=exclusion.attribute_id,
                    aggregate_id=str(exclusion.id),
                )
            )

            # 4. Register with UoW, delete, commit
            self._uow.register_aggregate(exclusion)
            await self._exclusion_repo.delete(command.exclusion_id)
            await self._uow.commit()

        # 5. Cache invalidation: L1 (family effective attrs) + L2 (storefront per-category)
        try:
            await invalidate_family_effective_cache(
                self._cache, self._family_repo, command.family_id
            )
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))

        self._logger.info(
            "family_exclusion_removed",
            exclusion_id=str(command.exclusion_id),
            family_id=str(command.family_id),
        )
