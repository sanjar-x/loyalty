"""
Command handler: bind an attribute to a family.

Validates that both the family and attribute exist, checks for duplicate
bindings, creates a new FamilyAttributeBinding, and cascades effective-
attribute cache invalidation to the family and all its descendants.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass
from typing import Any

from src.modules.catalog.domain.entities import FamilyAttributeBinding
from src.modules.catalog.domain.events import FamilyAttributeBindingCreatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeFamilyNotFoundError,
    AttributeNotFoundError,
    FamilyAttributeBindingAlreadyExistsError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeFamilyRepository,
    IAttributeRepository,
    IFamilyAttributeBindingRepository,
)
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class BindAttributeToFamilyCommand:
    """Input for binding an attribute to a family.

    Attributes:
        family_id: UUID of the target attribute family.
        attribute_id: UUID of the attribute to bind.
        sort_order: Display ordering of the attribute within the family.
        requirement_level: Required / recommended / optional.
        flag_overrides: Optional per-family overrides for global behavior flags.
        filter_settings: Optional per-family filter configuration.
    """

    family_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int = 0
    requirement_level: RequirementLevel = RequirementLevel.OPTIONAL
    flag_overrides: dict[str, Any] | None = None
    filter_settings: dict[str, Any] | None = None


@dataclass(frozen=True)
class BindAttributeToFamilyResult:
    """Output of attribute-to-family binding.

    Attributes:
        binding_id: UUID of the newly created binding.
    """

    binding_id: uuid.UUID


class BindAttributeToFamilyHandler:
    """Bind an attribute to a family with duplicate and existence checks.

    Attributes:
        _family_repo: AttributeFamily repository port.
        _attribute_repo: Attribute repository port.
        _binding_repo: FamilyAttributeBinding repository port.
        _uow: Unit of Work for transactional writes.
        _cache: Cache service for effective attribute cache invalidation.
        _logger: Structured logger with handler context.
    """

    def __init__(
        self,
        family_repo: IAttributeFamilyRepository,
        attribute_repo: IAttributeRepository,
        binding_repo: IFamilyAttributeBindingRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._family_repo = family_repo
        self._attribute_repo = attribute_repo
        self._binding_repo = binding_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="BindAttributeToFamilyHandler")

    async def handle(
        self, command: BindAttributeToFamilyCommand
    ) -> BindAttributeToFamilyResult:
        """Execute the bind-attribute-to-family command.

        Args:
            command: Binding creation parameters.

        Returns:
            Result containing the new binding's ID.

        Raises:
            AttributeFamilyNotFoundError: If the family does not exist.
            AttributeNotFoundError: If the attribute does not exist.
            FamilyAttributeBindingAlreadyExistsError: If the pair is already bound.
        """
        async with self._uow:
            family = await self._family_repo.get(command.family_id)
            if family is None:
                raise AttributeFamilyNotFoundError(family_id=command.family_id)

            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            if await self._binding_repo.check_binding_exists(
                family_id=command.family_id,
                attribute_id=command.attribute_id,
            ):
                raise FamilyAttributeBindingAlreadyExistsError(
                    family_id=command.family_id,
                    attribute_id=command.attribute_id,
                )

            binding = FamilyAttributeBinding.create(
                family_id=command.family_id,
                attribute_id=command.attribute_id,
                sort_order=command.sort_order,
                requirement_level=command.requirement_level,
                flag_overrides=command.flag_overrides,
                filter_settings=command.filter_settings,
            )

            binding.add_domain_event(
                FamilyAttributeBindingCreatedEvent(
                    binding_id=binding.id,
                    family_id=command.family_id,
                    attribute_id=command.attribute_id,
                    aggregate_id=str(binding.id),
                )
            )

            binding = await self._binding_repo.add(binding)
            self._uow.register_aggregate(binding)
            await self._uow.commit()

        try:
            descendant_ids = await self._family_repo.get_descendant_ids(
                command.family_id
            )
            all_ids = [command.family_id, *descendant_ids]
            keys = [f"family:{fid}:effective_attrs" for fid in all_ids]
            await self._cache.delete_many(keys)
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))

        return BindAttributeToFamilyResult(binding_id=binding.id)
