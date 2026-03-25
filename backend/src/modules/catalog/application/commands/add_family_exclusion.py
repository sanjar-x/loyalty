"""
Command handler: add a family attribute exclusion.

Validates that the target attribute is actually inherited from ancestor
families (not a direct binding), then creates a ``FamilyAttributeExclusion``
record and invalidates effective-attribute caches for the family and all
its descendants.

Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import family_effective_attrs_cache_key
from src.modules.catalog.domain.entities import FamilyAttributeExclusion
from src.modules.catalog.domain.events import FamilyAttributeExclusionAddedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeFamilyNotFoundError,
    AttributeNotFoundError,
    AttributeNotInheritedError,
    FamilyAttributeExclusionAlreadyExistsError,
    FamilyExclusionConflictsWithOwnBindingError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeFamilyRepository,
    IAttributeRepository,
    IFamilyAttributeBindingRepository,
    IFamilyAttributeExclusionRepository,
)
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AddFamilyExclusionCommand:
    """Input for adding an attribute exclusion to a family.

    Attributes:
        family_id: UUID of the family to add the exclusion to.
        attribute_id: UUID of the inherited attribute to exclude.
    """

    family_id: uuid.UUID
    attribute_id: uuid.UUID


@dataclass(frozen=True)
class AddFamilyExclusionResult:
    """Output of adding a family attribute exclusion.

    Attributes:
        exclusion_id: UUID of the newly created exclusion.
    """

    exclusion_id: uuid.UUID


class AddFamilyExclusionHandler:
    """Add an exclusion for an inherited attribute on a family.

    This is the most complex handler because it must resolve the ancestor
    chain and compute the effective attribute set to verify the attribute
    is actually inherited before allowing the exclusion.
    """

    def __init__(
        self,
        family_repo: IAttributeFamilyRepository,
        attribute_repo: IAttributeRepository,
        binding_repo: IFamilyAttributeBindingRepository,
        exclusion_repo: IFamilyAttributeExclusionRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._family_repo = family_repo
        self._attribute_repo = attribute_repo
        self._binding_repo = binding_repo
        self._exclusion_repo = exclusion_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="AddFamilyExclusionHandler")

    async def handle(
        self, command: AddFamilyExclusionCommand
    ) -> AddFamilyExclusionResult:
        """Execute the add-family-exclusion command.

        Args:
            command: Exclusion creation parameters.

        Returns:
            Result containing the new exclusion's ID.

        Raises:
            AttributeFamilyNotFoundError: If the family does not exist.
            AttributeNotFoundError: If the attribute does not exist.
            FamilyExclusionConflictsWithOwnBindingError: If the attribute
                has a direct binding on this family.
            AttributeNotInheritedError: If the attribute is not inherited
                from any ancestor family.
            FamilyAttributeExclusionAlreadyExistsError: If an exclusion
                for this pair already exists.
        """
        async with self._uow:
            # 1. Load family, validate exists
            family = await self._family_repo.get(command.family_id)
            if family is None:
                raise AttributeFamilyNotFoundError(family_id=command.family_id)

            # 2. Load attribute, validate exists
            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            # 3. Check NOT in own bindings
            has_own_binding = await self._binding_repo.check_binding_exists(
                command.family_id, command.attribute_id
            )
            if has_own_binding:
                raise FamilyExclusionConflictsWithOwnBindingError(
                    family_id=command.family_id,
                    attribute_id=command.attribute_id,
                )

            # 4. Resolve ancestor effective attributes to verify inheritance
            chain = await self._family_repo.get_ancestor_chain(command.family_id)
            ancestor_ids = [f.id for f in chain if f.id != command.family_id]

            if not ancestor_ids:
                # No ancestors means attribute can't be inherited
                raise AttributeNotInheritedError(
                    family_id=command.family_id,
                    attribute_id=command.attribute_id,
                )

            ancestor_bindings = await self._binding_repo.get_bindings_for_families(
                ancestor_ids
            )
            ancestor_exclusions = (
                await self._exclusion_repo.get_exclusions_for_families(ancestor_ids)
            )

            # Walk the chain root→parent (excluding self) to compute effective set
            effective_attr_ids: set[uuid.UUID] = set()
            for ancestor in chain:
                if ancestor.id == command.family_id:
                    break  # don't include self
                # Remove excluded attributes at this ancestor level
                for exc_attr_id in ancestor_exclusions.get(ancestor.id, set()):
                    effective_attr_ids.discard(exc_attr_id)
                # Add own bindings at this ancestor level
                for binding in ancestor_bindings.get(ancestor.id, []):
                    effective_attr_ids.add(binding.attribute_id)

            if command.attribute_id not in effective_attr_ids:
                raise AttributeNotInheritedError(
                    family_id=command.family_id,
                    attribute_id=command.attribute_id,
                )

            # 5. Check exclusion doesn't already exist
            already_excluded = await self._exclusion_repo.check_exclusion_exists(
                command.family_id, command.attribute_id
            )
            if already_excluded:
                raise FamilyAttributeExclusionAlreadyExistsError(
                    family_id=command.family_id,
                    attribute_id=command.attribute_id,
                )

            # 6. Create the exclusion entity
            exclusion = FamilyAttributeExclusion.create(
                family_id=command.family_id,
                attribute_id=command.attribute_id,
            )

            # 7. Emit domain event
            exclusion.add_domain_event(
                FamilyAttributeExclusionAddedEvent(
                    exclusion_id=exclusion.id,
                    family_id=command.family_id,
                    attribute_id=command.attribute_id,
                    aggregate_id=str(exclusion.id),
                )
            )

            # 8. Persist, register with UoW, commit
            exclusion = await self._exclusion_repo.add(exclusion)
            self._uow.register_aggregate(exclusion)
            await self._uow.commit()

        # 9. Cache invalidation: family + all descendants
        await self._invalidate_family_caches(command.family_id)

        return AddFamilyExclusionResult(exclusion_id=exclusion.id)

    async def _invalidate_family_caches(self, family_id: uuid.UUID) -> None:
        """Invalidate effective-attribute caches for a family and all descendants."""
        try:
            descendant_ids = await self._family_repo.get_descendant_ids(family_id)
            all_ids = [family_id, *descendant_ids]
            cache_keys = [family_effective_attrs_cache_key(fid) for fid in all_ids]
            await self._cache.delete_many(cache_keys)
        except Exception as exc:
            self._logger.warning(
                "cache_invalidation_failed",
                family_id=str(family_id),
                error=str(exc),
            )
