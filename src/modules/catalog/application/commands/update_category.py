import contextlib
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
class UpdateCategoryCommand:
    category_id: uuid.UUID
    name: str | None = None
    slug: str | None = None
    sort_order: int | None = None


@dataclass(frozen=True)
class UpdateCategoryResult:
    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None


class UpdateCategoryHandler:
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
        async with self._uow:
            category: Category | None = await self._category_repo.get_for_update(
                command.category_id
            )
            if category is None:
                raise CategoryNotFoundError(category_id=command.category_id)

            if command.slug is not None and command.slug != category.slug:
                if await self._category_repo.check_slug_exists_excluding(
                    command.slug, category.parent_id, command.category_id
                ):
                    raise CategorySlugConflictError(slug=command.slug, parent_id=category.parent_id)

            old_full_slug = category.update(
                name=command.name,
                slug=command.slug,
                sort_order=command.sort_order,
            )

            await self._category_repo.update(category)
            self._uow.register_aggregate(category)

            if old_full_slug is not None:
                await self._category_repo.update_descendants_full_slug(
                    old_prefix=old_full_slug,
                    new_prefix=category.full_slug,
                )

            await self._uow.commit()

        with contextlib.suppress(Exception):
            await self._cache.delete(CATEGORY_TREE_CACHE_KEY)

        self._logger.info("Категория обновлена", category_id=str(category.id))

        return UpdateCategoryResult(
            id=category.id,
            name=category.name,
            slug=category.slug,
            full_slug=category.full_slug,
            level=category.level,
            sort_order=category.sort_order,
            parent_id=category.parent_id,
        )
