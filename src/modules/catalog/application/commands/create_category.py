# src/modules/catalog/application/commands/create_category.py
import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import Category
from src.modules.catalog.domain.exceptions import (
    CategoryNotFoundError,
    CategorySlugConflictError,
)
from src.modules.catalog.domain.interfaces import ICategoryRepository
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.uow import IUnitOfWork

CACHE_KEY = "catalog:category_tree"


@dataclass(frozen=True)
class CreateCategoryCommand:
    name: str
    slug: str
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


@dataclass(frozen=True)
class CreateCategoryResult:
    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None


class CreateCategoryHandler:
    """Обработчик команды. Содержит только логику создания."""

    def __init__(
        self, category_repo: ICategoryRepository, uow: IUnitOfWork, cache: ICacheService
    ):
        self._category_repo: ICategoryRepository = category_repo
        self._uow: IUnitOfWork = uow
        self._cache: ICacheService = cache

    async def handle(self, command: CreateCategoryCommand) -> CreateCategoryResult:
        async with self._uow:
            is_slug_taken = await self._category_repo.check_slug_exists(
                slug=command.slug, parent_id=command.parent_id
            )
            if is_slug_taken:
                raise CategorySlugConflictError(
                    slug=command.slug, parent_id=command.parent_id
                )

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
            await self._uow.commit()
            await self._cache.delete(CACHE_KEY)

            return CreateCategoryResult(
                id=category.id,
                name=category.name,
                slug=category.slug,
                full_slug=category.full_slug,
                level=category.level,
                sort_order=category.sort_order,
                parent_id=category.parent_id,
            )
