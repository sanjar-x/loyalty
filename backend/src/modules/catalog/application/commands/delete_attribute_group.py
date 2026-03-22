"""
Command handler: delete an attribute group.

Validates the group exists, is not the protected "general" group,
and either moves attributes to the "general" group or rejects if it has
attributes. Emits ``AttributeGroupDeletedEvent``.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import GENERAL_GROUP_CODE
from src.modules.catalog.domain.events import AttributeGroupDeletedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeGroupCannotDeleteGeneralError,
    AttributeGroupHasAttributesError,
    AttributeGroupNotFoundError,
)
from src.modules.catalog.domain.interfaces import IAttributeGroupRepository
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteAttributeGroupCommand:
    """Input for deleting an attribute group.

    Attributes:
        group_id: UUID of the attribute group to delete.
        move_to_general: If True, move existing attributes to the "general"
            group before deletion. If False, reject deletion when attributes
            exist.
    """

    group_id: uuid.UUID
    move_to_general: bool = True


class DeleteAttributeGroupHandler:
    """Delete an existing attribute group by ID.

    If the group has attributes, either moves them to the "general" group
    (when ``move_to_general=True``) or raises an error.
    """

    def __init__(
        self,
        group_repo: IAttributeGroupRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._group_repo = group_repo
        self._uow = uow

    async def handle(self, command: DeleteAttributeGroupCommand) -> None:
        """Execute the delete-attribute-group command.

        Args:
            command: Attribute group deletion parameters.

        Raises:
            AttributeGroupNotFoundError: If the group does not exist.
            AttributeGroupCannotDeleteGeneralError: If attempting to delete "general".
            AttributeGroupHasAttributesError: If move_to_general is False and group has attributes.
        """
        async with self._uow:
            group = await self._group_repo.get(command.group_id)
            if group is None:
                raise AttributeGroupNotFoundError(group_id=command.group_id)

            if group.code == GENERAL_GROUP_CODE:
                raise AttributeGroupCannotDeleteGeneralError()

            has_attrs = await self._group_repo.has_attributes(command.group_id)
            if has_attrs:
                if command.move_to_general:
                    general = await self._group_repo.get_by_code(GENERAL_GROUP_CODE)
                    if general is None:
                        raise ValueError(
                            f"Cannot move attributes: '{GENERAL_GROUP_CODE}' group does not exist"
                        )
                    await self._group_repo.move_attributes_to_group(
                        source_group_id=command.group_id,
                        target_group_id=general.id,
                    )
                else:
                    raise AttributeGroupHasAttributesError(group_id=command.group_id)

            group.add_domain_event(
                AttributeGroupDeletedEvent(
                    group_id=group.id,
                    code=group.code,
                    aggregate_id=str(group.id),
                )
            )

            self._uow.register_aggregate(group)
            await self._group_repo.delete(command.group_id)
            await self._uow.commit()
