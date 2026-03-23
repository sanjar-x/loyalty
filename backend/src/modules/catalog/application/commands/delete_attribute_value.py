"""
Command handler: delete an attribute value.

Verifies the value exists and belongs to the given attribute.
Emits ``AttributeValueDeletedEvent`` through the parent attribute.
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.events import AttributeValueDeletedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeNotFoundError,
    AttributeValueInUseError,
    AttributeValueNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeValueRepository,
)
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteAttributeValueCommand:
    """Input for deleting an attribute value."""

    attribute_id: uuid.UUID
    value_id: uuid.UUID


class DeleteAttributeValueHandler:
    """Delete an attribute value by ID."""

    def __init__(
        self,
        attribute_repo: IAttributeRepository,
        value_repo: IAttributeValueRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._attribute_repo = attribute_repo
        self._value_repo = value_repo
        self._uow = uow

    async def handle(self, command: DeleteAttributeValueCommand) -> None:
        """Execute the delete-attribute-value command.

        Raises:
            AttributeNotFoundError: If the parent attribute does not exist.
            AttributeValueNotFoundError: If the value does not exist.
        """
        async with self._uow:
            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            value = await self._value_repo.get(command.value_id)
            if value is None or value.attribute_id != command.attribute_id:
                raise AttributeValueNotFoundError(value_id=command.value_id)

            if await self._value_repo.has_product_references(command.value_id):
                raise AttributeValueInUseError(value_id=command.value_id)

            attribute.add_domain_event(
                AttributeValueDeletedEvent(
                    attribute_id=attribute.id,
                    value_id=value.id,
                    code=value.code,
                    aggregate_id=str(attribute.id),
                )
            )

            self._uow.register_aggregate(attribute)
            await self._value_repo.delete(command.value_id)
            await self._uow.commit()
