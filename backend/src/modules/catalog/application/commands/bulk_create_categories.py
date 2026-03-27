"""
Command handler: bulk-create categories in a single transaction.

Supports flat lists (all items reference existing parent_id) and nested
trees (items reference each other via ``parent_ref`` — a client-supplied
key resolved within the batch). Computes full_slug, level, and
effective_template_id for each category.

Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.application.constants import CATEGORY_TREE_CACHE_KEY
from src.modules.catalog.domain.entities import Category
from src.modules.catalog.domain.events import CategoryCreatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeTemplateNotFoundError,
    CategoryNotFoundError,
    CategorySlugConflictError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeTemplateRepository,
    ICategoryRepository,
)
from src.shared.exceptions import ValidationError
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

MAX_BULK_CATEGORIES = 200


@dataclass(frozen=True)
class BulkCategoryItem:
    """A single category within a bulk-create request.

    Attributes:
        name_i18n: Multilingual display name.
        slug: URL-safe identifier, unique within parent level.
        parent_id: UUID of an existing parent category, or None for root.
        parent_ref: Client-supplied key referencing another item's ``ref``
            within the same batch (for building trees in one request).
            Mutually exclusive with ``parent_id``.
        ref: Client-supplied key so other items can reference this one
            as their parent via ``parent_ref``.
        sort_order: Display ordering among siblings.
        template_id: Optional FK to an AttributeTemplate.
    """

    name_i18n: dict[str, str]
    slug: str
    parent_id: uuid.UUID | None = None
    parent_ref: str | None = None
    ref: str | None = None
    sort_order: int = 0
    template_id: uuid.UUID | None = None


@dataclass(frozen=True)
class BulkCreateCategoriesCommand:
    """Input for bulk-creating categories.

    Attributes:
        items: List of category items to create (max 200).
        skip_existing: Silently skip categories with conflicting slug at
            the same parent level.
    """

    items: list[BulkCategoryItem]
    skip_existing: bool = False


@dataclass(frozen=True)
class BulkCategoryCreatedItem:
    """Info about a single created category."""

    id: uuid.UUID
    slug: str
    full_slug: str
    level: int
    ref: str | None = None


@dataclass(frozen=True)
class BulkCreateCategoriesResult:
    """Output of bulk category creation.

    Attributes:
        created_count: Number of categories successfully created.
        skipped_count: Number skipped due to slug conflict.
        created: Details of created categories.
        skipped_slugs: Slugs that were skipped.
    """

    created_count: int
    skipped_count: int
    created: list[BulkCategoryCreatedItem]
    skipped_slugs: list[str] = field(default_factory=list)


class BulkCreateCategoriesHandler:
    """Bulk-create categories with intra-batch parent resolution.

    Items are processed in order. Items with ``parent_ref`` are resolved
    to the ``ref`` of a previously created item in the same batch.
    This allows creating an entire subtree in one API call.
    """

    def __init__(
        self,
        category_repo: ICategoryRepository,
        template_repo: IAttributeTemplateRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._category_repo = category_repo
        self._template_repo = template_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="BulkCreateCategoriesHandler")

    async def handle(
        self, command: BulkCreateCategoriesCommand
    ) -> BulkCreateCategoriesResult:
        if len(command.items) > MAX_BULK_CATEGORIES:
            raise ValidationError(
                message=f"Bulk operation supports at most {MAX_BULK_CATEGORIES} items.",
                error_code="BULK_LIMIT_EXCEEDED",
                details={"max": MAX_BULK_CATEGORIES, "received": len(command.items)},
            )

        # Validate refs are unique within batch
        refs = [item.ref for item in command.items if item.ref]
        if len(refs) != len(set(refs)):
            raise ValidationError(
                message="Duplicate ref keys within the batch.",
                error_code="BULK_DUPLICATE_REFS",
            )

        # Validate no item has both parent_id and parent_ref
        for item in command.items:
            if item.parent_id is not None and item.parent_ref is not None:
                raise ValidationError(
                    message=f"Item '{item.slug}': parent_id and parent_ref are mutually exclusive.",
                    error_code="BULK_PARENT_CONFLICT",
                    details={"slug": item.slug},
                )

        async with self._uow:
            # ref → created Category (for intra-batch parent resolution)
            ref_map: dict[str, Category] = {}
            created: list[BulkCategoryCreatedItem] = []
            skipped_slugs: list[str] = []

            for item in command.items:
                # Resolve parent
                parent: Category | None = None

                if item.parent_ref is not None:
                    parent = ref_map.get(item.parent_ref)
                    if parent is None:
                        raise ValidationError(
                            message=f"Item '{item.slug}': parent_ref '{item.parent_ref}' not found in batch.",
                            error_code="BULK_PARENT_REF_NOT_FOUND",
                            details={"slug": item.slug, "parent_ref": item.parent_ref},
                        )
                elif item.parent_id is not None:
                    parent = await self._category_repo.get(item.parent_id)
                    if parent is None:
                        raise CategoryNotFoundError(category_id=item.parent_id)

                # Check slug uniqueness at this level
                parent_id = parent.id if parent else None
                if await self._category_repo.check_slug_exists(item.slug, parent_id):
                    if command.skip_existing:
                        skipped_slugs.append(item.slug)
                        continue
                    raise CategorySlugConflictError(slug=item.slug, parent_id=parent_id)

                # Validate template_id
                if item.template_id is not None:
                    template = await self._template_repo.get(item.template_id)
                    if template is None:
                        raise AttributeTemplateNotFoundError(template_id=item.template_id)

                # Create domain entity
                if parent is not None:
                    category = Category.create_child(
                        name_i18n=item.name_i18n,
                        slug=item.slug,
                        parent=parent,
                        sort_order=item.sort_order,
                        template_id=item.template_id,
                    )
                else:
                    category = Category.create_root(
                        name_i18n=item.name_i18n,
                        slug=item.slug,
                        sort_order=item.sort_order,
                        template_id=item.template_id,
                    )

                category = await self._category_repo.add(category)
                category.add_domain_event(
                    CategoryCreatedEvent(
                        category_id=category.id,
                        slug=category.slug,
                        aggregate_id=str(category.id),
                    )
                )
                self._uow.register_aggregate(category)

                if item.ref:
                    ref_map[item.ref] = category

                created.append(BulkCategoryCreatedItem(
                    id=category.id,
                    slug=category.slug,
                    full_slug=category.full_slug,
                    level=category.level,
                    ref=item.ref,
                ))

            await self._uow.commit()

        try:
            await self._cache.delete(CATEGORY_TREE_CACHE_KEY)
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))

        self._logger.info(
            "Categories bulk-created",
            created=len(created),
            skipped=len(skipped_slugs),
        )
        return BulkCreateCategoriesResult(
            created_count=len(created),
            skipped_count=len(skipped_slugs),
            created=created,
            skipped_slugs=skipped_slugs,
        )
