"""
Command handler: create a new attribute family.

Validates code uniqueness, creates either a root or child family, and emits
an ``AttributeFamilyCreatedEvent``. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import AttributeFamily
from src.modules.catalog.domain.events import AttributeFamilyCreatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeFamilyCodeAlreadyExistsError,
    AttributeFamilyNotFoundError,
)
from src.modules.catalog.domain.interfaces import IAttributeFamilyRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateAttributeFamilyCommand:
    """Input for creating a new attribute family.

    Attributes:
        code: Machine-readable unique code (e.g. "electronics", "clothing").
        name_i18n: Multilingual display name. Must have at least one entry.
        description_i18n: Optional multilingual description.
        parent_id: Parent family UUID, or None for a root family.
        sort_order: Display ordering among siblings.
    """

    code: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str] | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


@dataclass(frozen=True)
class CreateAttributeFamilyResult:
    """Output of attribute family creation.

    Attributes:
        id: UUID of the newly created attribute family.
    """

    id: uuid.UUID


class CreateAttributeFamilyHandler:
    """Create a new root or child attribute family with code uniqueness validation."""

    def __init__(
        self,
        family_repo: IAttributeFamilyRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._family_repo = family_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateAttributeFamilyHandler")

    async def handle(
        self, command: CreateAttributeFamilyCommand
    ) -> CreateAttributeFamilyResult:
        """Execute the create-attribute-family command.

        Args:
            command: Attribute family creation parameters.

        Returns:
            Result containing the new family's ID.

        Raises:
            AttributeFamilyCodeAlreadyExistsError: If the code is already taken.
            AttributeFamilyNotFoundError: If the specified parent does not exist.
        """
        async with self._uow:
            if await self._family_repo.check_code_exists(command.code):
                raise AttributeFamilyCodeAlreadyExistsError(code=command.code)

            if command.parent_id is not None:
                parent = await self._family_repo.get(command.parent_id)
                if parent is None:
                    raise AttributeFamilyNotFoundError(family_id=command.parent_id)

                family = AttributeFamily.create_child(
                    parent=parent,
                    code=command.code,
                    name_i18n=command.name_i18n,
                    description_i18n=command.description_i18n,
                    sort_order=command.sort_order,
                )
            else:
                family = AttributeFamily.create_root(
                    code=command.code,
                    name_i18n=command.name_i18n,
                    description_i18n=command.description_i18n,
                    sort_order=command.sort_order,
                )

            family.add_domain_event(
                AttributeFamilyCreatedEvent(
                    family_id=family.id,
                    code=family.code,
                    parent_id=family.parent_id,
                    aggregate_id=str(family.id),
                )
            )

            family = await self._family_repo.add(family)
            self._uow.register_aggregate(family)
            await self._uow.commit()

        return CreateAttributeFamilyResult(id=family.id)
