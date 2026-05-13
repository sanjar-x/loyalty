"""
Command handler: create a new attribute group.

Validates code uniqueness, persists the AttributeGroup aggregate, and emits
a domain event. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import AttributeGroup
from src.modules.catalog.domain.events import AttributeGroupCreatedEvent
from src.modules.catalog.domain.exceptions import AttributeGroupCodeConflictError
from src.modules.catalog.domain.interfaces import IAttributeGroupRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateAttributeGroupCommand:
    """Input for creating a new attribute group.

    Attributes:
        code: Machine-readable unique code (e.g. "general", "physical").
        name_i18n: Multilingual display name.
        sort_order: Display ordering among groups (lower = first).
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
    """Create a new attribute group with a unique code."""

    def __init__(
        self,
        group_repo: IAttributeGroupRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._group_repo = group_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateAttributeGroupHandler")

    async def handle(
        self, command: CreateAttributeGroupCommand
    ) -> CreateAttributeGroupResult:
        """Execute the create-attribute-group command.

        Args:
            command: Attribute group creation parameters.

        Returns:
            Result containing the group ID.

        Raises:
            AttributeGroupCodeConflictError: If the code is already taken.
        """
        async with self._uow:
            if await self._group_repo.check_code_exists(command.code):
                raise AttributeGroupCodeConflictError(code=command.code)

            group = AttributeGroup.create(
                code=command.code,
                name_i18n=command.name_i18n,
                sort_order=command.sort_order,
            )
            group = await self._group_repo.add(group)
            group.add_domain_event(
                AttributeGroupCreatedEvent(
                    group_id=group.id,
                    code=group.code,
                    aggregate_id=str(group.id),
                )
            )
            self._uow.register_aggregate(group)
            await self._uow.commit()

        self._logger.info("Attribute group created", group_id=str(group.id))

        return CreateAttributeGroupResult(group_id=group.id)
