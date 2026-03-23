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
from src.modules.catalog.domain.entities import Category
from src.modules.catalog.domain.exceptions import (
    CategoryNotFoundError,
    CategorySlugConflictError,
)
from src.modules.catalog.domain.interfaces import ICategoryRepository
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateCategoryCommand:
    """Input for updating a category.

    Attributes:
        category_id: UUID of the category to update.
        name: New display name, or None to keep current.
        slug: New URL-safe slug, or None to keep current.
        sort_order: New sort position, or None to keep current.
    """

    category_id: uuid.UUID
    name: str | None = None
    slug: str | None = None
    sort_order: int | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class UpdateCategoryResult:
    """Output of category update.

    Attributes:
        id: UUID of the updated category.
        name: Updated display name.
        slug: Updated URL-safe slug.
        full_slug: Recomputed materialized path.
        level: Tree depth.
        sort_order: Updated sort position.
        parent_id: Parent category UUID, or None.
    """

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None


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
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ):
        self._category_repo: ICategoryRepository = category_repo
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
                raise CategorySlugConflictError(slug=command.slug, parent_id=category.parent_id)

            _SAFE_FIELDS = frozenset({"name", "slug", "sort_order"})
            safe_fields = command._provided_fields & _SAFE_FIELDS
            update_kwargs: dict[str, Any] = {f: getattr(command, f) for f in safe_fields}
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
            self._logger.warning("Failed to invalidate category tree cache", error=str(e))

        self._logger.info("Category updated", category_id=str(category.id))

        return UpdateCategoryResult(
            id=category.id,
            name=category.name,
            slug=category.slug,
            full_slug=category.full_slug,
            level=category.level,
            sort_order=category.sort_order,
            parent_id=category.parent_id,
        )
