"""
Command handler: update an existing category.

Validates slug uniqueness, applies partial updates, cascades full_slug
changes to descendants, and invalidates the tree cache.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from types import EllipsisType
from typing import Any

from src.modules.catalog.application.constants import (
    CATEGORY_TREE_CACHE_KEY,
    storefront_card_cache_key,
    storefront_comparison_cache_key,
    storefront_filters_cache_key,
    storefront_form_cache_key,
)
from src.modules.catalog.domain.entities import Category
from src.modules.catalog.domain.events import CategoryUpdatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeTemplateNotFoundError,
    CategoryNotFoundError,
    CategorySlugConflictError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeTemplateRepository,
    ICategoryRepository,
)
from shared.exceptions import OptimisticLockError
from shared.interfaces.cache import ICacheService
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateCategoryCommand:
    """Input for updating a category.

    Attributes:
        category_id: UUID of the category to update.
        name_i18n: New multilingual display name, or None to keep current.
        slug: New URL-safe slug, or None to keep current.
        sort_order: New sort position, or None to keep current.
        template_id: New AttributeTemplate FK, None to clear, or ``...`` (default) to keep current.
    """

    category_id: uuid.UUID
    name_i18n: dict[str, str] | None = None
    slug: str | None = None
    sort_order: int | None = None
    template_id: uuid.UUID | None | EllipsisType = ...
    _provided_fields: frozenset[str] = field(default_factory=frozenset)
    expected_version: int | None = None
    """T-1.2 — when set, the handler enforces optimistic locking before
    mutating: aggregate ``version`` mismatch raises
    :class:`OptimisticLockError`. ``None`` (default) keeps the legacy
    last-write-wins behaviour for clients that haven't adopted ETag /
    If-Match yet."""


@dataclass(frozen=True)
class UpdateCategoryResult:
    """Output of category update.

    Attributes:
        id: UUID of the updated category.
        name_i18n: Updated multilingual display name.
        slug: Updated URL-safe slug.
        full_slug: Recomputed materialized path.
        level: Tree depth.
        sort_order: Updated sort position.
        parent_id: Parent category UUID, or None.
        template_id: Associated AttributeTemplate UUID, or None.
    """

    id: uuid.UUID
    name_i18n: dict[str, str]
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None
    template_id: uuid.UUID | None = None
    effective_template_id: uuid.UUID | None = None
    version: int = 0


class UpdateCategoryHandler:
    """Apply partial updates to an existing category with descendant cascade.

    Attributes:
        _category_repo: Category repository port.
        _uow: Unit of Work for transactional writes.
        _cache: Cache service for tree cache invalidation.
        _logger: Structured logger with handler context.
    """

    def __init__(
        self,
        category_repo: ICategoryRepository,
        template_repo: IAttributeTemplateRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ):
        self._category_repo: ICategoryRepository = category_repo
        self._template_repo: IAttributeTemplateRepository = template_repo
        self._uow: IUnitOfWork = uow
        self._cache: ICacheService = cache
        self._logger: ILogger = logger.bind(handler="UpdateCategoryHandler")

    async def handle(self, command: UpdateCategoryCommand) -> UpdateCategoryResult:
        """Execute the update-category command.

        Args:
            command: Category update parameters.

        Returns:
            Result containing the updated category state.

        Raises:
            CategoryNotFoundError: If the category does not exist.
            CategorySlugConflictError: If the new slug collides at the same level.
        """
        async with self._uow:
            if command.template_id is not ... and command.template_id is not None:
                template = await self._template_repo.get(command.template_id)
                if template is None:
                    raise AttributeTemplateNotFoundError(
                        template_id=command.template_id
                    )

            category: Category | None = await self._category_repo.get_for_update(
                command.category_id
            )
            if category is None:
                raise CategoryNotFoundError(category_id=command.category_id)

            # T-1.2 — early optimistic-lock check when an expected
            # version was provided (typically via the router's
            # ``If-Match`` header). Mismatch surfaces as
            # :class:`OptimisticLockError` (409); the router upgrades
            # it to 412 ``PRECONDITION_FAILED`` when the client used
            # If-Match.
            if (
                command.expected_version is not None
                and command.expected_version != category.version
            ):
                raise OptimisticLockError(
                    entity_type="Category",
                    entity_id=category.id,
                    expected_version=command.expected_version,
                    actual_version=category.version,
                )

            if (
                command.slug is not None
                and command.slug != category.slug
                and await self._category_repo.check_slug_exists_excluding(
                    command.slug, category.parent_id, command.category_id
                )
            ):
                raise CategorySlugConflictError(
                    slug=command.slug, parent_id=category.parent_id
                )

            _SAFE_FIELDS = frozenset({"name_i18n", "slug", "sort_order"})
            safe_fields = command._provided_fields & _SAFE_FIELDS
            update_kwargs: dict[str, Any] = {
                f: getattr(command, f) for f in safe_fields
            }

            # template_id uses Ellipsis sentinel; only pass through when explicitly provided
            template_id_changed = False
            if command.template_id is not ...:
                old_template_id = category.template_id
                update_kwargs["template_id"] = command.template_id
                template_id_changed = command.template_id != old_template_id

            old_full_slug = category.update(**update_kwargs)

            # Scenario C: clear template_id → re-inherit from parent
            if template_id_changed and command.template_id is None:
                if category.parent_id is not None:
                    parent = await self._category_repo.get(category.parent_id)
                    new_effective = parent.effective_template_id if parent else None
                else:
                    new_effective = None
                category.set_effective_template_id(new_effective)

            # T-1.2 — repo.update() returns a freshly-mapped domain
            # entity built from the post-flush ORM row, so its
            # ``version`` reflects the SQLAlchemy-side bump. Lift the
            # value back onto the original ``category`` so the response
            # carries the new ETag without losing the in-memory
            # ``domain_events`` list.
            persisted = await self._category_repo.update(category)
            category.version = persisted.version
            category.add_domain_event(
                CategoryUpdatedEvent(
                    category_id=category.id,
                    aggregate_id=str(category.id),
                )
            )
            self._uow.register_aggregate(category)

            # Propagate effective_template_id to inheriting descendants
            affected_category_ids: list[uuid.UUID] = []
            if template_id_changed:
                descendant_ids = (
                    await self._category_repo.propagate_effective_template_id(
                        category.id, category.effective_template_id
                    )
                )
                affected_category_ids = [category.id, *descendant_ids]

            if old_full_slug is not None:
                await self._category_repo.update_descendants_full_slug(
                    old_prefix=old_full_slug,
                    new_prefix=category.full_slug,
                )

            await self._uow.commit()

        try:
            await self._cache.delete(CATEGORY_TREE_CACHE_KEY)
        except Exception as e:
            self._logger.warning(
                "Failed to invalidate category tree cache", error=str(e)
            )

        if affected_category_ids:
            try:
                keys = []
                for cat_id in affected_category_ids:
                    keys.append(storefront_filters_cache_key(cat_id))
                    keys.append(storefront_card_cache_key(cat_id))
                    keys.append(storefront_comparison_cache_key(cat_id))
                    keys.append(storefront_form_cache_key(cat_id))
                await self._cache.delete_many(keys)
            except Exception as e:
                self._logger.warning(
                    "Failed to invalidate storefront caches after template_id change",
                    error=str(e),
                    affected_count=len(affected_category_ids),
                )

        self._logger.info("Category updated", category_id=str(category.id))

        return UpdateCategoryResult(
            id=category.id,
            name_i18n=category.name_i18n,
            slug=category.slug,
            full_slug=category.full_slug,
            level=category.level,
            sort_order=category.sort_order,
            parent_id=category.parent_id,
            template_id=category.template_id,
            effective_template_id=category.effective_template_id,
            version=category.version,
        )
