"""
Command handler: create a new attribute.

Validates code/slug uniqueness, persists the Attribute aggregate, and emits
an ``AttributeCreatedEvent``. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.domain.entities import Attribute
from src.modules.catalog.domain.events import AttributeCreatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeCodeConflictError,
    AttributeSlugConflictError,
)
from src.modules.catalog.domain.interfaces import IAttributeRepository
from src.modules.catalog.domain.value_objects import (
    DEFAULT_SEARCH_WEIGHT,
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
)
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateAttributeCommand:
    """Input for creating a new attribute.

    Attributes:
        code: Machine-readable unique code.
        slug: URL-safe unique identifier.
        name_i18n: Multilingual display name. At least one language required.
        data_type: Primitive storage type.
        ui_type: Widget hint for storefront rendering.
        is_dictionary: Whether attribute has predefined option values.
        group_id: UUID of the attribute group.
        description_i18n: Optional multilingual description.
        level: Product or variant level.
        is_filterable: Show as filter on storefront.
        is_searchable: Include in full-text search.
        search_weight: Search ranking priority 1-10.
        is_comparable: Include in comparison table.
        is_visible_on_card: Show on product detail page.
        is_visible_in_catalog: Show in listing preview.
        validation_rules: Type-specific validation constraints.
    """

    code: str
    slug: str
    name_i18n: dict[str, str]
    data_type: AttributeDataType
    ui_type: AttributeUIType
    is_dictionary: bool
    group_id: uuid.UUID
    description_i18n: dict[str, str] = field(default_factory=dict)
    level: AttributeLevel = AttributeLevel.PRODUCT
    is_filterable: bool = False
    is_searchable: bool = False
    search_weight: int = DEFAULT_SEARCH_WEIGHT
    is_comparable: bool = False
    is_visible_on_card: bool = False
    is_visible_in_catalog: bool = False
    validation_rules: dict[str, Any] | None = None


@dataclass(frozen=True)
class CreateAttributeResult:
    """Output of attribute creation.

    Attributes:
        attribute_id: UUID of the newly created attribute.
    """

    attribute_id: uuid.UUID


class CreateAttributeHandler:
    """Create a new attribute with code/slug uniqueness validation."""

    def __init__(
        self,
        attribute_repo: IAttributeRepository,
        uow: IUnitOfWork,
    ):
        self._attribute_repo = attribute_repo
        self._uow = uow

    async def handle(self, command: CreateAttributeCommand) -> CreateAttributeResult:
        """Execute the create-attribute command.

        Args:
            command: Attribute creation parameters.

        Returns:
            Result containing the attribute ID.

        Raises:
            AttributeCodeConflictError: If the code is already taken.
            AttributeSlugConflictError: If the slug is already taken.
            ValueError: If name_i18n is empty, search_weight out of range,
                or validation_rules invalid.
        """
        async with self._uow:
            if await self._attribute_repo.check_code_exists(command.code):
                raise AttributeCodeConflictError(code=command.code)

            if await self._attribute_repo.check_slug_exists(command.slug):
                raise AttributeSlugConflictError(slug=command.slug)

            attribute = Attribute.create(
                code=command.code,
                slug=command.slug,
                name_i18n=command.name_i18n,
                description_i18n=command.description_i18n,
                data_type=command.data_type,
                ui_type=command.ui_type,
                is_dictionary=command.is_dictionary,
                group_id=command.group_id,
                level=command.level,
                is_filterable=command.is_filterable,
                is_searchable=command.is_searchable,
                search_weight=command.search_weight,
                is_comparable=command.is_comparable,
                is_visible_on_card=command.is_visible_on_card,
                is_visible_in_catalog=command.is_visible_in_catalog,
                validation_rules=command.validation_rules,
            )

            attribute.add_domain_event(
                AttributeCreatedEvent(
                    attribute_id=attribute.id,
                    code=attribute.code,
                    aggregate_id=str(attribute.id),
                )
            )

            attribute = await self._attribute_repo.add(attribute)
            self._uow.register_aggregate(attribute)
            await self._uow.commit()

        return CreateAttributeResult(attribute_id=attribute.id)
