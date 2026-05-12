"""
Command handler: bulk reorder attribute values.

Receives a list of (value_id, sort_order) pairs and updates them atomically.
All values must belong to the specified attribute.
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.domain.events import AttributeValuesReorderedEvent
from src.modules.catalog.domain.exceptions import AttributeNotFoundError
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeValueRepository,
)
from src.shared.exceptions import ValidationError
from src.shared.interfaces.logger import ILogger
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
        logger: ILogger,
    ):
        self._attribute_repo = attribute_repo
        self._value_repo = value_repo
        self._uow = uow
        self._logger = logger.bind(handler="ReorderAttributeValuesHandler")

    async def handle(self, command: ReorderAttributeValuesCommand) -> None:
        """Execute the reorder-attribute-values command.

        Raises:
            AttributeNotFoundError: If the parent attribute does not exist.
        """
        if not command.items:
            return

        all_ids = [item.value_id for item in command.items]
        if len(all_ids) != len(set(all_ids)):
            seen: set[uuid.UUID] = set()
            dups = {vid for vid in all_ids if vid in seen or seen.add(vid)}
            raise ValidationError(
                message=f"Duplicate value_id(s) in reorder request: {dups}",
                details={"duplicate_ids": [str(d) for d in dups]},
            )

        async with self._uow:
            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            valid_ids = await self._value_repo.list_ids_by_attribute(
                command.attribute_id
            )
            requested_ids = set(all_ids)
            invalid_ids = requested_ids - valid_ids
            if invalid_ids:
                raise ValidationError(
                    message=f"Value IDs {invalid_ids} do not belong to attribute {command.attribute_id}",
                    details={"invalid_ids": [str(i) for i in invalid_ids]},
                )

            updates = [(item.value_id, item.sort_order) for item in command.items]
            await self._value_repo.bulk_update_sort_order(updates)
            attribute.add_domain_event(
                AttributeValuesReorderedEvent(
                    attribute_id=command.attribute_id,
                    aggregate_id=str(command.attribute_id),
                )
            )
            self._uow.register_aggregate(attribute)
            await self._uow.commit()
