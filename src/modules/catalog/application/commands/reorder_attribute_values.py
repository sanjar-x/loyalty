"""
Command handler: bulk reorder attribute values.

Receives a list of (value_id, sort_order) pairs and updates them atomically.
All values must belong to the specified attribute.
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.domain.exceptions import AttributeNotFoundError
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeValueRepository,
)
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ReorderItem:
    """A single value reorder instruction."""

    value_id: uuid.UUID
    sort_order: int


@dataclass(frozen=True)
class ReorderAttributeValuesCommand:
    """Input for bulk-reordering attribute values.

    Attributes:
        attribute_id: UUID of the parent attribute.
        items: List of reorder instructions.
    """

    attribute_id: uuid.UUID
    items: list[ReorderItem] = field(default_factory=list)


class ReorderAttributeValuesHandler:
    """Bulk-update sort order for attribute values atomically."""

    def __init__(
        self,
        attribute_repo: IAttributeRepository,
        value_repo: IAttributeValueRepository,
        uow: IUnitOfWork,
    ):
        self._attribute_repo = attribute_repo
        self._value_repo = value_repo
        self._uow = uow

    async def handle(self, command: ReorderAttributeValuesCommand) -> None:
        """Execute the reorder-attribute-values command.

        Raises:
            AttributeNotFoundError: If the parent attribute does not exist.
        """
        if not command.items:
            return

        async with self._uow:
            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            updates = [(item.value_id, item.sort_order) for item in command.items]
            await self._value_repo.bulk_update_sort_order(updates)
            await self._uow.commit()
