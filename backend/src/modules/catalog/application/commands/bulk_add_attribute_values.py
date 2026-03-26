"""
Command handler: bulk-add values to a dictionary attribute.

Validates the parent attribute is a dictionary type, checks code/slug
uniqueness both within the batch and against existing values, persists
all values, and emits an ``AttributeValueAddedEvent`` for each.
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
    InvalidColorHexError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeTemplateRepository,
    IAttributeValueRepository,
    ITemplateAttributeBindingRepository,
)
from src.modules.catalog.domain.value_objects import (
    AttributeUIType,
    validate_i18n_completeness,
)
from src.shared.exceptions import ValidationError
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class BulkValueItem:
    """A single value item within a bulk-add request.

    Attributes:
        code: Machine-readable code (unique within attribute).
        slug: URL-safe identifier (unique within attribute).
        value_i18n: Multilingual display name.
        search_aliases: Search synonyms list.
        meta_data: Arbitrary metadata (e.g. hex color).
        value_group: Optional grouping label.
        sort_order: Display ordering.
    """

    code: str
    slug: str
    value_i18n: dict[str, str]
    search_aliases: list[str] = field(default_factory=list)
    meta_data: dict[str, Any] = field(default_factory=dict)
    value_group: str | None = None
    sort_order: int = 0


@dataclass(frozen=True)
class BulkAddAttributeValuesCommand:
    """Input for bulk-adding values to an attribute.

    Attributes:
        attribute_id: UUID of the parent attribute.
        items: List of value items to create (max 100).
    """

    attribute_id: uuid.UUID
    items: list[BulkValueItem]


@dataclass(frozen=True)
class BulkAddAttributeValuesResult:
    """Output of bulk attribute value creation."""

    created_count: int
    ids: list[uuid.UUID]


class BulkAddAttributeValuesHandler:
    """Bulk-add new values to a dictionary attribute."""

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
        self._logger = logger.bind(handler="BulkAddAttributeValuesHandler")

    async def handle(
        self, command: BulkAddAttributeValuesCommand
    ) -> BulkAddAttributeValuesResult:
        """Execute the bulk-add-attribute-values command.

        Raises:
            ValidationError: If more than 100 items or duplicates within batch.
            AttributeNotFoundError: If the parent attribute does not exist.
            AttributeNotDictionaryError: If the attribute is not a dictionary.
            AttributeValueCodeConflictError: If a code is taken.
            AttributeValueSlugConflictError: If a slug is taken.
        """
        for item in command.items:
            validate_i18n_completeness(item.value_i18n, "value_i18n")

        if len(command.items) > 100:
            raise ValidationError(
                message="Bulk operation supports at most 100 items.",
                error_code="BULK_LIMIT_EXCEEDED",
                details={"max": 100, "received": len(command.items)},
            )

        # Check for duplicate codes within the batch
        batch_codes = [item.code for item in command.items]
        if len(batch_codes) != len(set(batch_codes)):
            code_counts: dict[str, int] = {}
            for c in batch_codes:
                code_counts[c] = code_counts.get(c, 0) + 1
            duplicates = [c for c, n in code_counts.items() if n > 1]
            raise ValidationError(
                message="Duplicate codes within the batch.",
                error_code="BULK_DUPLICATE_CODES",
                details={"duplicate_codes": duplicates},
            )

        # Check for duplicate slugs within the batch
        batch_slugs = [item.slug for item in command.items]
        if len(batch_slugs) != len(set(batch_slugs)):
            slug_counts: dict[str, int] = {}
            for s in batch_slugs:
                slug_counts[s] = slug_counts.get(s, 0) + 1
            duplicates_slugs = [s for s, n in slug_counts.items() if n > 1]
            raise ValidationError(
                message="Duplicate slugs within the batch.",
                error_code="BULK_DUPLICATE_SLUGS",
                details={"duplicate_slugs": duplicates_slugs},
            )

        async with self._uow:
            # 1. Validate attribute exists and is dictionary
            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            if not attribute.is_dictionary:
                raise AttributeNotDictionaryError(attribute_id=command.attribute_id)

            # 1b. Validate color hex if color_swatch
            if attribute.ui_type == AttributeUIType.COLOR_SWATCH:
                import re

                _hex_re = re.compile(r"^#[0-9a-fA-F]{6}$")
                for item in command.items:
                    if item.meta_data:
                        hex_val = item.meta_data.get("hex")
                        if hex_val is not None and not _hex_re.match(hex_val):
                            raise InvalidColorHexError(hex_value=hex_val)

            # 2. Batch-check code uniqueness against existing values
            existing_codes = await self._value_repo.check_codes_exist(
                command.attribute_id, batch_codes
            )
            if existing_codes:
                first_conflict = next(iter(existing_codes))
                raise AttributeValueCodeConflictError(
                    code=first_conflict, attribute_id=command.attribute_id
                )

            # 3. Batch-check slug uniqueness against existing values
            existing_slugs = await self._value_repo.check_slugs_exist(
                command.attribute_id, batch_slugs
            )
            if existing_slugs:
                first_conflict = next(iter(existing_slugs))
                raise AttributeValueSlugConflictError(
                    slug=first_conflict, attribute_id=command.attribute_id
                )

            # 4. Create all domain entities and persist them
            created_ids: list[uuid.UUID] = []

            for item in command.items:
                value = AttributeValue.create(
                    attribute_id=command.attribute_id,
                    code=item.code,
                    slug=item.slug,
                    value_i18n=item.value_i18n,
                    search_aliases=item.search_aliases,
                    meta_data=item.meta_data,
                    value_group=item.value_group,
                    sort_order=item.sort_order,
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
                created_ids.append(value.id)

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

        return BulkAddAttributeValuesResult(
            created_count=len(created_ids),
            ids=created_ids,
        )
