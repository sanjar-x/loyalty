# src\modules\storage\presentation\dependencies.py
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession


from src.modules.catalog.domain.interfaces import ICategoryRepository
from src.modules.storage.infrastructure.repository import StorageObjectRepository
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.uow import IUnitOfWork


class StorageProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_storage_repo(self, session: AsyncSession) -> ICategoryRepository:
        return StorageObjectRepository(session)