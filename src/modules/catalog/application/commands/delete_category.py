import contextlib
import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import CATEGORY_TREE_CACHE_KEY
from src.modules.catalog.domain.exceptions import (
    CategoryHasChildrenError,
    CategoryNotFoundError,
)
from src.modules.catalog.domain.interfaces import ICategoryRepository
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteCategoryCommand:
    category_id: uuid.UUID


class DeleteCategoryHandler:
    def __init__(
        self,
        category_repo: ICategoryRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ):
        self._category_repo = category_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="DeleteCategoryHandler")

    async def handle(self, command: DeleteCategoryCommand) -> None:
        async with self._uow:
            category = await self._category_repo.get(command.category_id)
            if category is None:
                raise CategoryNotFoundError(category_id=command.category_id)

            has_children = await self._category_repo.has_children(command.category_id)
            if has_children:
                raise CategoryHasChildrenError(category_id=command.category_id)

            self._uow.register_aggregate(category)
            await self._category_repo.delete(command.category_id)
            await self._uow.commit()

        with contextlib.suppress(Exception):
            await self._cache.delete(CATEGORY_TREE_CACHE_KEY)

        self._logger.info("Категория удалена", category_id=str(command.category_id))
