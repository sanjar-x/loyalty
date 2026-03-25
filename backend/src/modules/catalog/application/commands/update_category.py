"""
Command handler: update an existing category.

Validates slug uniqueness, applies partial updates, cascades full_slug
changes to descendants, and invalidates the tree cache.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.application.constants import CATEGORY_TREE_CACHE_KEY
from src.modules.catalog.application.queries.storefront import (
    invalidate_storefront_cache,
)
from src.modules.catalog.domain.entities import Category
from src.modules.catalog.domain.exceptions import (
    AttributeFamilyNotFoundError,
    CategoryNotFoundError,
    CategorySlugConflictError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeFamilyRepository,
    ICategoryRepository,
)
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateCategoryCommand:
    """Input for updating a category.

    Attributes:
        category_id: UUID of the category to update.
        name_i18n: New multilingual display name, or None to keep current.
        slug: New URL-safe slug, or None to keep current.
        sort_order: New sort position, or None to keep current.
        family_id: New AttributeFamily FK, None to clear, or ``...`` (default) to keep current.
    """

    category_id: uuid.UUID
    name_i18n: dict[str, str] | None = None
    slug: str | None = None
    sort_order: int | None = None
    family_id: uuid.UUID | None = ...  # type: ignore[assignment]
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


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
        family_id: Associated AttributeFamily UUID, or None.
    """

    id: uuid.UUID
    name_i18n: dict[str, str]
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None
    family_id: uuid.UUID | None = None


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
        family_repo: IAttributeFamilyRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ):
        self._category_repo: ICategoryRepository = category_repo
        self._family_repo: IAttributeFamilyRepository = family_repo
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
        if command.family_id is not ... and command.family_id is not None:
            family = await self._family_repo.get(command.family_id)
            if family is None:
                raise AttributeFamilyNotFoundError(family_id=command.family_id)

        async with self._uow:
            category: Category | None = await self._category_repo.get_for_update(
                command.category_id
            )
            if category is None:
                raise CategoryNotFoundError(category_id=command.category_id)

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

            # family_id uses Ellipsis sentinel; only pass through when explicitly provided
            family_id_changed = False
            if command.family_id is not ...:
                old_family_id = category.family_id
                update_kwargs["family_id"] = command.family_id
                family_id_changed = command.family_id != old_family_id

            old_full_slug = category.update(**update_kwargs)

            await self._category_repo.update(category)
            self._uow.register_aggregate(category)

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

        if family_id_changed:
            try:
                await invalidate_storefront_cache(self._cache, command.category_id)
            except Exception as e:
                self._logger.warning(
                    "Failed to invalidate storefront cache after family_id change",
                    error=str(e),
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
            family_id=category.family_id,
        )
