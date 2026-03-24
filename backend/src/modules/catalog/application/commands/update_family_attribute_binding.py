"""
Command handler: update a family-attribute binding.

Loads the binding, validates ownership, applies partial updates to mutable
fields, emits an update event, and cascades effective-attribute cache
invalidation to the family and all its descendants.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.domain.events import FamilyAttributeBindingUpdatedEvent
from src.modules.catalog.domain.exceptions import (
    FamilyAttributeBindingNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeFamilyRepository,
    IFamilyAttributeBindingRepository,
)
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateFamilyAttributeBindingCommand:
    """Input for updating a family-attribute binding.

    Attributes:
        binding_id: UUID of the binding to update.
        family_id: UUID of the family that owns the binding (ownership guard).
        sort_order: New display ordering, or None to keep current.
        requirement_level: New requirement level, or None to keep current.
        flag_overrides: New flag overrides, or None to keep current.
        filter_settings: New filter settings, or None to keep current.
        _provided_fields: Set of field names explicitly provided by the caller.
    """

    binding_id: uuid.UUID
    family_id: uuid.UUID
    sort_order: int | None = None
    requirement_level: RequirementLevel | None = None
    flag_overrides: dict[str, Any] | None = None
    filter_settings: dict[str, Any] | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


class UpdateFamilyAttributeBindingHandler:
    """Apply partial updates to a family-attribute binding.

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
        self._logger = logger.bind(handler="UpdateFamilyAttributeBindingHandler")

    async def handle(self, command: UpdateFamilyAttributeBindingCommand) -> None:
        """Execute the update-family-attribute-binding command.

        Args:
            command: Binding update parameters.

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

            _SAFE_FIELDS = frozenset(
                {"sort_order", "requirement_level", "flag_overrides", "filter_settings"}
            )
            safe_fields = command._provided_fields & _SAFE_FIELDS
            update_kwargs: dict[str, Any] = {
                f: getattr(command, f) for f in safe_fields
            }

            if update_kwargs:
                binding.update(**update_kwargs)

            binding.add_domain_event(
                FamilyAttributeBindingUpdatedEvent(
                    binding_id=binding.id,
                    aggregate_id=str(binding.id),
                )
            )

            await self._binding_repo.update(binding)
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
