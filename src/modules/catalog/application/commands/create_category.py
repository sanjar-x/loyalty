# src/modules/catalog/application/commands/create_category.py
import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import Category
from src.modules.catalog.domain.exceptions import (
    CategoryMaxDepthError,
    CategoryNotFoundError,
    CategorySlugConflictError,
)
from src.modules.catalog.domain.interfaces import ICategoryRepository
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.uow import IUnitOfWork

MAX_CATEGORY_DEPTH = 3
CACHE_KEY = "catalog:category_tree"


@dataclass(frozen=True)
class CreateCategoryCommand:
    name: str
    slug: str
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


class CreateCategoryHandler:
    """Обработчик команды. Содержит только логику создания."""

    def __init__(
        self, category_repo: ICategoryRepository, uow: IUnitOfWork, cache: ICacheService
    ):
        self._category_repo: ICategoryRepository = category_repo
        self._uow: IUnitOfWork = uow
        self._cache: ICacheService = cache

    async def handle(self, command: CreateCategoryCommand):
        async with self._uow:
            is_slug_taken = await self._category_repo.check_slug_exists(
                slug=command.slug, parent_id=command.parent_id
            )
            if is_slug_taken:
                raise CategorySlugConflictError(
                    slug=command.slug, parent_id=command.parent_id
                )

            level = 0
            full_slug = command.slug

            if command.parent_id is not None:
                parent = await self._category_repo.get(command.parent_id)
                if parent is None:
                    raise CategoryNotFoundError(category_id=command.parent_id)

                if parent.level >= MAX_CATEGORY_DEPTH:
                    raise CategoryMaxDepthError(
                        max_depth=MAX_CATEGORY_DEPTH, current_level=parent.level
                    )

                level = parent.level + 1
                full_slug = f"{parent.full_slug}/{command.slug}"

            category = Category.create(
                name=command.name,
                slug=command.slug,
                parent_id=command.parent_id,
                level=level,
                full_slug=full_slug,
                sort_order=command.sort_order,
            )

            category = await self._category_repo.add(category)
            await self._uow.commit()
            await self._cache.delete(CACHE_KEY)

            return category
