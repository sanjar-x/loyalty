"""
Command handler: add a new value to a dictionary attribute.

Validates the parent attribute is a dictionary type, checks code/slug
uniqueness within the attribute, persists the value, and emits an
``AttributeValueAddedEvent``.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.domain.entities import AttributeValue
from src.modules.catalog.domain.events import AttributeValueAddedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeNotDictionaryError,
    AttributeNotFoundError,
    AttributeValueCodeConflictError,
    AttributeValueSlugConflictError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeValueRepository,
)
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AddAttributeValueCommand:
    """Input for adding a value to an attribute.

    Attributes:
        attribute_id: UUID of the parent attribute.
        code: Machine-readable code (unique within attribute).
        slug: URL-safe identifier (unique within attribute).
        value_i18n: Multilingual display name.
        search_aliases: Search synonyms list.
        meta_data: Arbitrary metadata (e.g. hex color).
        value_group: Optional grouping label.
        sort_order: Display ordering.
    """

    attribute_id: uuid.UUID
    code: str
    slug: str
    value_i18n: dict[str, str]
    search_aliases: list[str] = field(default_factory=list)
    meta_data: dict[str, Any] = field(default_factory=dict)
    value_group: str | None = None
    sort_order: int = 0


@dataclass(frozen=True)
class AddAttributeValueResult:
    """Output of attribute value creation."""

    value_id: uuid.UUID


class AddAttributeValueHandler:
    """Add a new value to a dictionary attribute."""

    def __init__(
        self,
        attribute_repo: IAttributeRepository,
        value_repo: IAttributeValueRepository,
        uow: IUnitOfWork,
    ):
        self._attribute_repo = attribute_repo
        self._value_repo = value_repo
        self._uow = uow

    async def handle(self, command: AddAttributeValueCommand) -> AddAttributeValueResult:
        """Execute the add-attribute-value command.

        Raises:
            AttributeNotFoundError: If the parent attribute does not exist.
            AttributeNotDictionaryError: If the attribute is not a dictionary.
            AttributeValueCodeConflictError: If the code is taken.
            AttributeValueSlugConflictError: If the slug is taken.
        """
        async with self._uow:
            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            if not attribute.is_dictionary:
                raise AttributeNotDictionaryError(attribute_id=command.attribute_id)

            if await self._value_repo.check_code_exists(command.attribute_id, command.code):
                raise AttributeValueCodeConflictError(
                    code=command.code, attribute_id=command.attribute_id
                )

            if await self._value_repo.check_slug_exists(command.attribute_id, command.slug):
                raise AttributeValueSlugConflictError(
                    slug=command.slug, attribute_id=command.attribute_id
                )

            value = AttributeValue.create(
                attribute_id=command.attribute_id,
                code=command.code,
                slug=command.slug,
                value_i18n=command.value_i18n,
                search_aliases=command.search_aliases,
                meta_data=command.meta_data,
                value_group=command.value_group,
                sort_order=command.sort_order,
            )

            attribute.add_domain_event(
                AttributeValueAddedEvent(
                    attribute_id=attribute.id,
                    value_id=value.id,
                    code=value.code,
                    aggregate_id=str(attribute.id),
                )
            )

            value = await self._value_repo.add(value)
            self._uow.register_aggregate(attribute)
            await self._uow.commit()

        return AddAttributeValueResult(value_id=value.id)
