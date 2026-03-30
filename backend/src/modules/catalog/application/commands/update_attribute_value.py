"""
Command handler: update an existing attribute value.

Applies partial updates to mutable fields. Code and slug are immutable.
Emits ``AttributeValueUpdatedEvent`` through the parent attribute.
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.application.queries.resolve_template_attributes import (
    collect_attribute_cache_keys,
)
from src.modules.catalog.domain.entities import AttributeValue
from src.modules.catalog.domain.events import AttributeValueUpdatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeNotFoundError,
    AttributeValueNotFoundError,
    InvalidColorHexError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeTemplateRepository,
    IAttributeValueRepository,
    ITemplateAttributeBindingRepository,
)
from src.modules.catalog.domain.value_objects import AttributeUIType
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass(frozen=True)
class UpdateAttributeValueCommand:
    """Input for updating an attribute value. Code and slug are immutable."""

    attribute_id: uuid.UUID
    value_id: uuid.UUID
    value_i18n: dict[str, str] | None = None
    search_aliases: list[str] | None = None
    meta_data: dict[str, Any] | None = None
    value_group: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


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
    is_active: bool


class UpdateAttributeValueHandler:
    """Apply partial updates to an existing attribute value."""

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
        self._logger = logger.bind(handler="UpdateAttributeValueHandler")

    async def handle(
        self, command: UpdateAttributeValueCommand
    ) -> UpdateAttributeValueResult:
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

            if (
                "meta_data" in command._provided_fields
                and command.meta_data
                and attribute.ui_type == AttributeUIType.COLOR_SWATCH
            ):
                hex_val = command.meta_data.get("hex")
                if hex_val is not None and not _HEX_COLOR_RE.match(hex_val):
                    raise InvalidColorHexError(hex_value=hex_val)

            # Only pass fields the client actually sent, intersected with
            # the entity's declared updatable fields (defence-in-depth).
            safe_fields = command._provided_fields & AttributeValue._UPDATABLE_FIELDS
            update_kwargs: dict[str, Any] = {
                name: getattr(command, name) for name in safe_fields
            }

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

            cache_keys = await collect_attribute_cache_keys(
                command.attribute_id,
                self._binding_repo,
                self._template_repo,
            )

            await self._uow.commit()

        try:
            if cache_keys:
                await self._cache.delete_many(cache_keys)
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))

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
            is_active=value.is_active,
        )
