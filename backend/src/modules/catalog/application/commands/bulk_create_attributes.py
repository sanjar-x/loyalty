"""
Command handler: bulk-create attributes in a single transaction.

Validates code/slug uniqueness within batch and against DB,
optionally validates group_id references, persists all Attribute
aggregates, and emits ``AttributeCreatedEvent`` for each.

Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.domain.entities import Attribute
from src.modules.catalog.domain.events import AttributeCreatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeCodeConflictError,
    AttributeGroupNotFoundError,
    AttributeSlugConflictError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeGroupRepository,
    IAttributeRepository,
)
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    validate_i18n_completeness,
)
from src.shared.exceptions import ValidationError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

MAX_BULK_ATTRIBUTES = 100
DEFAULT_SEARCH_WEIGHT = 5


@dataclass(frozen=True)
class BulkAttributeItem:
    """A single attribute within a bulk-create request."""

    code: str
    slug: str
    name_i18n: dict[str, str]
    data_type: AttributeDataType
    ui_type: AttributeUIType
    is_dictionary: bool = True
    group_id: uuid.UUID | None = None
    description_i18n: dict[str, str] | None = None
    level: AttributeLevel = AttributeLevel.PRODUCT
    is_filterable: bool = False
    is_searchable: bool = False
    search_weight: int = DEFAULT_SEARCH_WEIGHT
    is_comparable: bool = False
    is_visible_on_card: bool = False
    validation_rules: dict[str, Any] | None = None


@dataclass(frozen=True)
class BulkCreateAttributesCommand:
    """Input for bulk-creating attributes.

    Attributes:
        items: List of attribute items to create (max 100).
        skip_existing: Silently skip attributes with existing code/slug.
    """

    items: list[BulkAttributeItem]
    skip_existing: bool = False


@dataclass(frozen=True)
class BulkCreateAttributesResult:
    """Output of bulk attribute creation."""

    created_count: int
    skipped_count: int
    ids: list[uuid.UUID]
    skipped_codes: list[str] = field(default_factory=list)


class BulkCreateAttributesHandler:
    """Bulk-create attributes with batch-level uniqueness validation."""

    def __init__(
        self,
        attribute_repo: IAttributeRepository,
        group_repo: IAttributeGroupRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._attribute_repo = attribute_repo
        self._group_repo = group_repo
        self._uow = uow
        self._logger = logger.bind(handler="BulkCreateAttributesHandler")

    async def handle(  # noqa: C901
        self, command: BulkCreateAttributesCommand
    ) -> BulkCreateAttributesResult:
        if len(command.items) > MAX_BULK_ATTRIBUTES:
            raise ValidationError(
                message=f"Bulk operation supports at most {MAX_BULK_ATTRIBUTES} items.",
                error_code="BULK_LIMIT_EXCEEDED",
                details={"max": MAX_BULK_ATTRIBUTES, "received": len(command.items)},
            )

        # Validate no duplicate codes within batch
        batch_codes = [item.code for item in command.items]
        if len(batch_codes) != len(set(batch_codes)):
            seen: set[str] = set()
            dupes = [c for c in batch_codes if c in seen or seen.add(c)]
            raise ValidationError(
                message="Duplicate codes within the batch.",
                error_code="BULK_DUPLICATE_CODES",
                details={"duplicate_codes": list(set(dupes))},
            )

        # Validate no duplicate slugs within batch
        batch_slugs = [item.slug for item in command.items]
        if len(batch_slugs) != len(set(batch_slugs)):
            seen_s: set[str] = set()
            dupes_s = [s for s in batch_slugs if s in seen_s or seen_s.add(s)]
            raise ValidationError(
                message="Duplicate slugs within the batch.",
                error_code="BULK_DUPLICATE_SLUGS",
                details={"duplicate_slugs": list(set(dupes_s))},
            )

        # Validate i18n completeness
        for item in command.items:
            validate_i18n_completeness(item.name_i18n, "name_i18n")

        async with self._uow:
            # Validate group_ids exist (batch-deduplicated)
            group_ids = {item.group_id for item in command.items if item.group_id}
            for gid in group_ids:
                if await self._group_repo.get(gid) is None:
                    raise AttributeGroupNotFoundError(group_id=gid)

            created_ids: list[uuid.UUID] = []
            skipped_codes: list[str] = []

            for item in command.items:
                code_taken = await self._attribute_repo.check_code_exists(item.code)
                slug_taken = await self._attribute_repo.check_slug_exists(item.slug)

                if code_taken or slug_taken:
                    if command.skip_existing:
                        skipped_codes.append(item.code)
                        continue
                    if code_taken:
                        raise AttributeCodeConflictError(code=item.code)
                    raise AttributeSlugConflictError(slug=item.slug)

                attribute = Attribute.create(
                    code=item.code,
                    slug=item.slug,
                    name_i18n=item.name_i18n,
                    description_i18n=item.description_i18n,
                    data_type=item.data_type,
                    ui_type=item.ui_type,
                    is_dictionary=item.is_dictionary,
                    group_id=item.group_id,
                    level=item.level,
                    is_filterable=item.is_filterable,
                    is_searchable=item.is_searchable,
                    search_weight=item.search_weight,
                    is_comparable=item.is_comparable,
                    is_visible_on_card=item.is_visible_on_card,
                    validation_rules=item.validation_rules,
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
                created_ids.append(attribute.id)

            await self._uow.commit()

        self._logger.info(
            "Attributes bulk-created",
            created=len(created_ids),
            skipped=len(skipped_codes),
        )
        return BulkCreateAttributesResult(
            created_count=len(created_ids),
            skipped_count=len(skipped_codes),
            ids=created_ids,
            skipped_codes=skipped_codes,
        )
