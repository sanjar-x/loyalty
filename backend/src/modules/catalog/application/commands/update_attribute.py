"""
Command handler: update an existing attribute.

Applies partial updates to mutable fields. Code, slug, and data_type are
immutable after creation. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.domain.events import AttributeUpdatedEvent
from src.modules.catalog.domain.exceptions import AttributeNotFoundError
from src.modules.catalog.domain.interfaces import IAttributeRepository
from src.modules.catalog.domain.value_objects import AttributeLevel, AttributeUIType
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateAttributeCommand:
    """Input for updating an attribute. Code, slug, and data_type are immutable.

    Attributes:
        attribute_id: UUID of the attribute to update.
        name_i18n: New multilingual name, or None to keep current.
        description_i18n: New multilingual description, or None to keep current.
        ui_type: New UI widget type, or None to keep current.
        group_id: New group UUID, or None to keep current.
        level: New attribute level, or None to keep current.
        is_filterable: New filter flag, or None to keep current.
        is_searchable: New search flag, or None to keep current.
        search_weight: New search weight, or None to keep current.
        is_comparable: New comparison flag, or None to keep current.
        is_visible_on_card: New card visibility flag, or None to keep current.
        is_visible_in_catalog: New catalog visibility flag, or None to keep current.
        validation_rules: New rules dict, None to clear, or absent to keep.
    """

    attribute_id: uuid.UUID
    name_i18n: dict[str, str] | None = None
    description_i18n: dict[str, str] | None = None
    ui_type: AttributeUIType | None = None
    group_id: uuid.UUID | None = None
    level: AttributeLevel | None = None
    is_filterable: bool | None = None
    is_searchable: bool | None = None
    search_weight: int | None = None
    is_comparable: bool | None = None
    is_visible_on_card: bool | None = None
    is_visible_in_catalog: bool | None = None
    validation_rules: dict[str, Any] | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class UpdateAttributeResult:
    """Output of attribute update -- the full attribute ID for confirmation."""

    id: uuid.UUID


class UpdateAttributeHandler:
    """Apply partial updates to an existing attribute."""

    def __init__(
        self,
        attribute_repo: IAttributeRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._attribute_repo = attribute_repo
        self._uow = uow

    async def handle(self, command: UpdateAttributeCommand) -> UpdateAttributeResult:
        """Execute the update-attribute command.

        Args:
            command: Attribute update parameters.

        Returns:
            Result containing the updated attribute ID.

        Raises:
            AttributeNotFoundError: If the attribute does not exist.
            ValueError: If name_i18n empty, search_weight out of range,
                or validation_rules incompatible with data_type.
        """
        async with self._uow:
            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            # Only pass fields the client actually sent (tracked via _provided_fields).
            update_kwargs: dict[str, Any] = {
                name: getattr(command, name) for name in command._provided_fields
            }

            attribute.update(**update_kwargs)

            attribute.add_domain_event(
                AttributeUpdatedEvent(
                    attribute_id=attribute.id,
                    aggregate_id=str(attribute.id),
                )
            )

            await self._attribute_repo.update(attribute)
            self._uow.register_aggregate(attribute)
            await self._uow.commit()

        return UpdateAttributeResult(id=attribute.id)
