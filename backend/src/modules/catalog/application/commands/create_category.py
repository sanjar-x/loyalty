"""
Command handler: create a new category.

Creates either a root or child category after validating slug uniqueness
at the target parent level. Invalidates the category tree cache on success.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

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
class CreateCategoryCommand:
    """Input for creating a new category.

    Attributes:
        name: Display name of the category.
        slug: URL-safe identifier, unique within the parent level.
        parent_id: Parent category UUID, or None for a root category.
        sort_order: Display ordering among siblings.
    """

    name: str
    slug: str
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


@dataclass(frozen=True)
class CreateCategoryResult:
    """Output of category creation.

    Attributes:
        id: UUID of the newly created category.
        name: Display name.
        slug: URL-safe identifier.
        full_slug: Materialized path (e.g. ``"electronics/phones"``).
        level: Depth in the tree (0 = root).
        sort_order: Display ordering.
        parent_id: Parent category UUID, or None.
    """

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None


class CreateCategoryHandler:
    """Create a new root or child category.

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
        self._logger: ILogger = logger.bind(handler="CreateCategoryHandler")

    async def handle(self, command: CreateCategoryCommand) -> CreateCategoryResult:
        """Execute the create-category command.

        Args:
            command: Category creation parameters.

        Returns:
            Result containing the new category's state.

        Raises:
            CategorySlugConflictError: If the slug collides at the target level.
            CategoryNotFoundError: If the specified parent does not exist.
            CategoryMaxDepthError: If the parent is already at max depth.
        """
        async with self._uow:
            is_slug_taken = await self._category_repo.check_slug_exists(
                slug=command.slug, parent_id=command.parent_id
            )
            if is_slug_taken:
                raise CategorySlugConflictError(slug=command.slug, parent_id=command.parent_id)

            if command.parent_id is not None:
                parent = await self._category_repo.get(command.parent_id)
                if parent is None:
                    raise CategoryNotFoundError(category_id=command.parent_id)

                category = Category.create_child(
                    name=command.name,
                    slug=command.slug,
                    parent=parent,
                    sort_order=command.sort_order,
                )
            else:
                category = Category.create_root(
                    name=command.name,
                    slug=command.slug,
                    sort_order=command.sort_order,
                )

            category = await self._category_repo.add(category)
            self._uow.register_aggregate(category)
            await self._uow.commit()

        try:
            await self._cache.delete(CATEGORY_TREE_CACHE_KEY)
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))

        return CreateCategoryResult(
            id=category.id,
            name=category.name,
            slug=category.slug,
            full_slug=category.full_slug,
            level=category.level,
            sort_order=category.sort_order,
            parent_id=category.parent_id,
        )
