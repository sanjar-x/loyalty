"""
Command handler: add a new value to a dictionary attribute.

Validates the parent attribute is a dictionary type, checks code/slug
uniqueness within the attribute, persists the value, and emits an
``AttributeValueAddedEvent``.
"""

import re
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
    InvalidColorHexError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeTemplateRepository,
    IAttributeValueRepository,
    ITemplateAttributeBindingRepository,
)
from src.modules.catalog.domain.value_objects import AttributeUIType, validate_i18n_completeness
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


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
        binding_repo: ITemplateAttributeBindingRepository,
        template_repo: IAttributeTemplateRepository,
        cache: ICacheService,
        uow: IUnitOfWork,
        logger: ILogger,
    ):
        self._attribute_repo = attribute_repo
        self._value_repo = value_repo
        self._binding_repo = binding_repo
        self._template_repo = template_repo
        self._cache = cache
        self._uow = uow
        self._logger = logger.bind(handler="AddAttributeValueHandler")

    async def handle(
        self, command: AddAttributeValueCommand
    ) -> AddAttributeValueResult:
        """Execute the add-attribute-value command.

        Raises:
            AttributeNotFoundError: If the parent attribute does not exist.
            AttributeNotDictionaryError: If the attribute is not a dictionary.
            AttributeValueCodeConflictError: If the code is taken.
            AttributeValueSlugConflictError: If the slug is taken.
        """
        validate_i18n_completeness(command.value_i18n, "value_i18n")

        async with self._uow:
            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            if not attribute.is_dictionary:
                raise AttributeNotDictionaryError(attribute_id=command.attribute_id)

            if attribute.ui_type == AttributeUIType.COLOR_SWATCH and command.meta_data:
                hex_val = command.meta_data.get("hex")
                if hex_val is not None and not _HEX_COLOR_RE.match(hex_val):
                    raise InvalidColorHexError(hex_value=hex_val)

            if await self._value_repo.check_code_exists(
                command.attribute_id, command.code
            ):
                raise AttributeValueCodeConflictError(
                    code=command.code, attribute_id=command.attribute_id
                )

            if await self._value_repo.check_slug_exists(
                command.attribute_id, command.slug
            ):
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

            from src.modules.catalog.application.queries.resolve_template_attributes import (
                collect_attribute_cache_keys,
            )
            cache_keys = await collect_attribute_cache_keys(
                command.attribute_id, self._binding_repo, self._template_repo,
            )

            await self._uow.commit()

        try:
            if cache_keys:
                await self._cache.delete_many(cache_keys)
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))

        return AddAttributeValueResult(value_id=value.id)
