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


_SENTINEL: object = object()


@dataclass(frozen=True)
class UpdateAttributeValueCommand:
    """Input for updating an attribute value. Code and slug are immutable."""

    attribute_id: uuid.UUID
    value_id: uuid.UUID
    value_i18n: dict[str, str] | None = None
    search_aliases: list[str] | None = None
    meta_data: dict[str, Any] | None = None
    value_group: str | None = _SENTINEL  # type: ignore[assignment]
    sort_order: int | None = None


@dataclass(frozen=True)
class UpdateAttributeValueResult:
    """Output of the update-attribute-value command."""

    id: uuid.UUID
    attribute_id: uuid.UUID
    code: str
    slug: str
    value_i18n: dict[str, str]
    search_aliases: list[str]
    meta_data: dict[str, Any] | None
    value_group: str | None
    sort_order: int


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

    async def handle(self, command: UpdateAttributeValueCommand) -> UpdateAttributeValueResult:
        """Execute the update-attribute-value command.

        Returns:
            Rich result containing the updated value fields.

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

            update_kwargs: dict[str, Any] = dict(
                value_i18n=command.value_i18n,
                search_aliases=command.search_aliases,
                meta_data=command.meta_data,
                sort_order=command.sort_order,
            )
            if command.value_group is not _SENTINEL:
                update_kwargs["value_group"] = command.value_group

            value.update(**update_kwargs)

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

        return UpdateAttributeValueResult(
            id=value.id,
            attribute_id=value.attribute_id,
            code=value.code,
            slug=value.slug,
            value_i18n=value.value_i18n,
            search_aliases=list(value.search_aliases) if value.search_aliases else [],
            meta_data=value.meta_data,
            value_group=value.value_group,
            sort_order=value.sort_order,
        )
