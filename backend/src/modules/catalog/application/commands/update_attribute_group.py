"""
Command handler: update an existing attribute group.

Applies partial updates (name_i18n, sort_order) to an attribute group.
Code is immutable and cannot be changed after creation.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.events import AttributeGroupUpdatedEvent
from src.modules.catalog.domain.exceptions import AttributeGroupNotFoundError
from src.modules.catalog.domain.interfaces import IAttributeGroupRepository
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateAttributeGroupCommand:
    """Input for updating an attribute group.

    Attributes:
        group_id: UUID of the attribute group to update.
        name_i18n: New multilingual name, or None to keep current.
        sort_order: New sort position, or None to keep current.
    """

    group_id: uuid.UUID
    name_i18n: dict[str, str] | None = None
    sort_order: int | None = None


@dataclass(frozen=True)
class UpdateAttributeGroupResult:
    """Output of attribute group update.

    Attributes:
        id: UUID of the updated group.
        code: Machine-readable group code (immutable).
        name_i18n: Updated multilingual name.
        sort_order: Updated sort position.
    """

    id: uuid.UUID
    code: str
    name_i18n: dict[str, str]
    sort_order: int


class UpdateAttributeGroupHandler:
    """Apply partial updates to an existing attribute group."""

    def __init__(
        self,
        attribute_group_repo: IAttributeGroupRepository,
        uow: IUnitOfWork,
    ):
        self._attribute_group_repo = group_repo
        self._uow = uow

    async def handle(self, command: UpdateAttributeGroupCommand) -> UpdateAttributeGroupResult:
        """Execute the update-attribute-group command.

        Args:
            command: Attribute group update parameters.

        Returns:
            Result containing the updated group state.

        Raises:
            AttributeGroupNotFoundError: If the group does not exist.
            ValueError: If name_i18n is provided but empty.
        """
        async with self._uow:
            group = await self._attribute_group_repo.get(command.group_id)
            if group is None:
                raise AttributeGroupNotFoundError(group_id=command.group_id)

            group.update(
                name_i18n=command.name_i18n,
                sort_order=command.sort_order,
            )

            group.add_domain_event(
                AttributeGroupUpdatedEvent(
                    group_id=group.id,
                    aggregate_id=str(group.id),
                )
            )

            await self._attribute_group_repo.update(group)
            self._uow.register_aggregate(group)
            await self._uow.commit()

        return UpdateAttributeGroupResult(
            id=group.id,
            code=group.code,
            name_i18n=group.name_i18n,
            sort_order=group.sort_order,
        )
