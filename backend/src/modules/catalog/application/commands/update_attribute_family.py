"""
Command handler: update an existing attribute family.

Applies partial updates (name_i18n, description_i18n, sort_order) to an
attribute family. Code, parent_id, and level are immutable after creation.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.domain.events import AttributeFamilyUpdatedEvent
from src.modules.catalog.domain.exceptions import AttributeFamilyNotFoundError
from src.modules.catalog.domain.interfaces import IAttributeFamilyRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateAttributeFamilyCommand:
    """Input for updating an attribute family.

    Attributes:
        family_id: UUID of the attribute family to update.
        name_i18n: New multilingual name, or None to keep current.
        description_i18n: New multilingual description, or None to keep current.
        sort_order: New sort position, or None to keep current.
        _provided_fields: Set of field names explicitly provided by the caller.
    """

    family_id: uuid.UUID
    name_i18n: dict[str, str] | None = None
    description_i18n: dict[str, str] | None = None
    sort_order: int | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class UpdateAttributeFamilyResult:
    """Output of attribute family update.

    Attributes:
        id: UUID of the updated family.
        code: Machine-readable family code (immutable).
        name_i18n: Updated multilingual name.
        description_i18n: Updated multilingual description.
        sort_order: Updated sort position.
        parent_id: Parent family UUID, or None.
        level: Depth in tree (0 = root).
    """

    id: uuid.UUID
    code: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    sort_order: int
    parent_id: uuid.UUID | None = None
    level: int = 0


class UpdateAttributeFamilyHandler:
    """Apply partial updates to an existing attribute family."""

    def __init__(
        self,
        family_repo: IAttributeFamilyRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._family_repo = family_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateAttributeFamilyHandler")

    async def handle(
        self, command: UpdateAttributeFamilyCommand
    ) -> UpdateAttributeFamilyResult:
        """Execute the update-attribute-family command.

        Args:
            command: Attribute family update parameters.

        Returns:
            Result containing the updated family state.

        Raises:
            AttributeFamilyNotFoundError: If the family does not exist.
        """
        async with self._uow:
            family = await self._family_repo.get(command.family_id)
            if family is None:
                raise AttributeFamilyNotFoundError(family_id=command.family_id)

            _SAFE_FIELDS = frozenset({"name_i18n", "description_i18n", "sort_order"})
            safe_fields = command._provided_fields & _SAFE_FIELDS
            update_kwargs: dict[str, Any] = {
                f: getattr(command, f) for f in safe_fields
            }
            family.update(**update_kwargs)

            family.add_domain_event(
                AttributeFamilyUpdatedEvent(
                    family_id=family.id,
                    aggregate_id=str(family.id),
                )
            )

            await self._family_repo.update(family)
            self._uow.register_aggregate(family)
            await self._uow.commit()

        self._logger.info(
            "Attribute family updated", family_id=str(family.id)
        )

        return UpdateAttributeFamilyResult(
            id=family.id,
            code=family.code,
            name_i18n=family.name_i18n,
            description_i18n=family.description_i18n,
            sort_order=family.sort_order,
            parent_id=family.parent_id,
            level=family.level,
        )
