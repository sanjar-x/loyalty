"""
Command handler: delete an attribute group.

Verifies the group exists and has no attributes, then removes it.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import GENERAL_GROUP_CODE
from src.modules.catalog.domain.events import AttributeGroupDeletedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeGroupHasAttributesError,
    AttributeGroupNotFoundError,
    AttributeGroupProtectedError,
)
from src.modules.catalog.domain.interfaces import IAttributeGroupRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteAttributeGroupCommand:
    """Input for deleting an attribute group.

    Attributes:
        group_id: UUID of the group to delete.
    """

    group_id: uuid.UUID


class DeleteAttributeGroupHandler:
    """Delete an existing attribute group by ID."""

    def __init__(
        self,
        group_repo: IAttributeGroupRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ):
        self._group_repo = group_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteAttributeGroupHandler")

    async def handle(self, command: DeleteAttributeGroupCommand) -> None:
        """Execute the delete-attribute-group command.

        Args:
            command: Attribute group deletion parameters.

        Raises:
            AttributeGroupNotFoundError: If the group does not exist.
            AttributeGroupProtectedError: If the group is the protected 'general' group.
            AttributeGroupHasAttributesError: If the group still has attributes.
        """
        async with self._uow:
            group = await self._group_repo.get_for_update(command.group_id)
            if group is None:
                raise AttributeGroupNotFoundError(group_id=command.group_id)

            if group.code == GENERAL_GROUP_CODE:
                raise AttributeGroupProtectedError()

            if await self._group_repo.has_attributes(command.group_id):
                raise AttributeGroupHasAttributesError(group_id=command.group_id)

            group.add_domain_event(
                AttributeGroupDeletedEvent(
                    group_id=group.id,
                    aggregate_id=str(group.id),
                )
            )
            self._uow.register_aggregate(group)
            await self._group_repo.delete(command.group_id)
            await self._uow.commit()

        self._logger.info("Attribute group deleted", group_id=str(command.group_id))
