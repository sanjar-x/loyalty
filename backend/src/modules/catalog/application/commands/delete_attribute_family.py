"""
Command handler: delete an attribute family.

Validates the family exists, has no children, and is not referenced by
categories before removing it. Emits ``AttributeFamilyDeletedEvent``.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.events import AttributeFamilyDeletedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeFamilyHasCategoryReferencesError,
    AttributeFamilyHasChildrenError,
    AttributeFamilyNotFoundError,
)
from src.modules.catalog.domain.interfaces import IAttributeFamilyRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteAttributeFamilyCommand:
    """Input for deleting an attribute family.

    Attributes:
        family_id: UUID of the attribute family to delete.
    """

    family_id: uuid.UUID


class DeleteAttributeFamilyHandler:
    """Delete an attribute family (leaf node with no category references).

    Attributes:
        _family_repo: AttributeFamily repository port.
        _uow: Unit of Work for transactional writes.
        _logger: Structured logger with handler context.
    """

    def __init__(
        self,
        family_repo: IAttributeFamilyRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._family_repo = family_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteAttributeFamilyHandler")

    async def handle(self, command: DeleteAttributeFamilyCommand) -> None:
        """Execute the delete-attribute-family command.

        Args:
            command: Attribute family deletion parameters.

        Raises:
            AttributeFamilyNotFoundError: If the family does not exist.
            AttributeFamilyHasChildrenError: If the family still has children.
            AttributeFamilyHasCategoryReferencesError: If categories reference this family.
        """
        async with self._uow:
            family = await self._family_repo.get(command.family_id)
            if family is None:
                raise AttributeFamilyNotFoundError(family_id=command.family_id)

            has_children = await self._family_repo.has_children(command.family_id)
            if has_children:
                raise AttributeFamilyHasChildrenError(family_id=command.family_id)

            has_category_refs = await self._family_repo.has_category_references(
                command.family_id
            )
            if has_category_refs:
                raise AttributeFamilyHasCategoryReferencesError(
                    family_id=command.family_id
                )

            family.add_domain_event(
                AttributeFamilyDeletedEvent(
                    family_id=family.id,
                    code=family.code,
                    aggregate_id=str(family.id),
                )
            )
            self._uow.register_aggregate(family)
            await self._family_repo.delete(command.family_id)
            await self._uow.commit()

        self._logger.info("Attribute family deleted", family_id=str(command.family_id))
