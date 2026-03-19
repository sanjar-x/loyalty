"""
Command handler: update an existing attribute value.

Applies partial updates to mutable fields. Code and slug are immutable.
Emits ``AttributeValueUpdatedEvent`` through the parent attribute.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from src.modules.catalog.domain.events import AttributeValueUpdatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeNotFoundError,
    AttributeValueNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeValueRepository,
)
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateAttributeValueCommand:
    """Input for updating an attribute value. Code and slug are immutable."""

    attribute_id: uuid.UUID
    value_id: uuid.UUID
    value_i18n: dict[str, str] | None = None
    search_aliases: list[str] | None = None
    meta_data: dict[str, Any] | None = None
    value_group: str | None = ...  # type: ignore[assignment]
    sort_order: int | None = None


class UpdateAttributeValueHandler:
    """Apply partial updates to an existing attribute value."""

    def __init__(
        self,
        attribute_repo: IAttributeRepository,
        value_repo: IAttributeValueRepository,
        uow: IUnitOfWork,
    ):
        self._attribute_repo = attribute_repo
        self._value_repo = value_repo
        self._uow = uow

    async def handle(self, command: UpdateAttributeValueCommand) -> uuid.UUID:
        """Execute the update-attribute-value command.

        Returns:
            UUID of the updated value.

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

            value.update(
                value_i18n=command.value_i18n,
                search_aliases=command.search_aliases,
                meta_data=command.meta_data,
                value_group=command.value_group,
                sort_order=command.sort_order,
            )

            attribute.add_domain_event(
                AttributeValueUpdatedEvent(
                    attribute_id=attribute.id,
                    value_id=value.id,
                    aggregate_id=str(attribute.id),
                )
            )

            await self._value_repo.update(value)
            self._uow.register_aggregate(attribute)
            await self._uow.commit()

        return value.id
