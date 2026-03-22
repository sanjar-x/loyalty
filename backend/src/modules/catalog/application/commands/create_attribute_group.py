"""
Command handler: create a new attribute group.

Validates code uniqueness, persists the AttributeGroup aggregate, and emits
an ``AttributeGroupCreatedEvent``. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import AttributeGroup
from src.modules.catalog.domain.events import AttributeGroupCreatedEvent
from src.modules.catalog.domain.exceptions import AttributeGroupCodeConflictError
from src.modules.catalog.domain.interfaces import IAttributeGroupRepository
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateAttributeGroupCommand:
    """Input for creating a new attribute group.

    Attributes:
        code: Machine-readable unique code (e.g. "physical", "technical").
        name_i18n: Multilingual display name. Must have at least one entry.
        sort_order: Display ordering among groups.
    """

    code: str
    name_i18n: dict[str, str]
    sort_order: int = 0


@dataclass(frozen=True)
class CreateAttributeGroupResult:
    """Output of attribute group creation.

    Attributes:
        group_id: UUID of the newly created attribute group.
    """

    group_id: uuid.UUID


class CreateAttributeGroupHandler:
    """Create a new attribute group with code uniqueness validation."""

    def __init__(
        self,
        group_repo: IAttributeGroupRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._group_repo = group_repo
        self._uow = uow

    async def handle(self, command: CreateAttributeGroupCommand) -> CreateAttributeGroupResult:
        """Execute the create-attribute-group command.

        Args:
            command: Attribute group creation parameters.

        Returns:
            Result containing the group ID.

        Raises:
            AttributeGroupCodeConflictError: If the code is already taken.
            ValueError: If name_i18n is empty.
        """
        async with self._uow:
            if await self._group_repo.check_code_exists(command.code):
                raise AttributeGroupCodeConflictError(code=command.code)

            group = AttributeGroup.create(
                code=command.code,
                name_i18n=command.name_i18n,
                sort_order=command.sort_order,
            )

            group.add_domain_event(
                AttributeGroupCreatedEvent(
                    group_id=group.id,
                    code=group.code,
                    aggregate_id=str(group.id),
                )
            )

            group = await self._group_repo.add(group)
            self._uow.register_aggregate(group)
            await self._uow.commit()

        return CreateAttributeGroupResult(group_id=group.id)
