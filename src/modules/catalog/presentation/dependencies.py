# src/modules/catalog/providers.py
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.commands.create_category import (
    CreateCategoryHandler,
)
from src.modules.catalog.application.queries.get_category_tree import (
    GetCategoryTreeHandler,
)
from src.modules.catalog.domain.interfaces import ICategoryRepository
from src.modules.catalog.infrastructure.repositories.category import CategoryRepository
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.uow import IUnitOfWork


class CategoryProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_category_repo(self, session: AsyncSession) -> ICategoryRepository:
        return CategoryRepository(session)

    @provide(scope=Scope.REQUEST)
    def provide_create_handler(
        self, repo: ICategoryRepository, uow: IUnitOfWork, cache: ICacheService
    ) -> CreateCategoryHandler:
        return CreateCategoryHandler(category_repo=repo, uow=uow, cache=cache)

    @provide(scope=Scope.REQUEST)
    def provide_tree_handler(
        self, repo: ICategoryRepository, cache: ICacheService
    ) -> GetCategoryTreeHandler:
        return GetCategoryTreeHandler(category_repo=repo, cache=cache)
