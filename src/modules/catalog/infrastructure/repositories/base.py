# src/modules/catalog/infrastructure/repositories/base.py
import uuid
from abc import abstractmethod
from typing import Any, Generic, TypeVar

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.interfaces import ICatalogRepository
from src.shared.interfaces.entities import IBase

ModelType = TypeVar("ModelType", bound=IBase)
EntityType = TypeVar("EntityType")


class BaseRepository(Generic[EntityType, ModelType], ICatalogRepository[EntityType]):
    """
    Базовый репозиторий, реализующий Data Mapper Pattern.
    Принимает и возвращает только доменные сущности (EntityType).
    """

    model: type[ModelType]

    def __init_subclass__(cls, model_class: type[ModelType] | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if model_class:
            cls.model = model_class

    def __init__(self, session: AsyncSession):
        self._session = session

    @abstractmethod
    def _to_domain(self, orm: ModelType) -> EntityType:
        pass

    @abstractmethod
    def _to_orm(self, entity: EntityType, orm: ModelType | None = None) -> ModelType:
        pass

    async def add(self, entity: EntityType) -> EntityType:
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, entity_id: uuid.UUID) -> EntityType | None:
        orm = await self._session.get(self.model, entity_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def update(self, entity: EntityType) -> EntityType:
        pk = getattr(entity, "id", None)
        if not pk:
            raise ValueError("Для обновления у доменной сущности должен быть id")

        orm = await self._session.get(self.model, pk)
        if not orm:
            raise ValueError(f"Сущность с id {pk} не найдена в БД")

        orm = self._to_orm(entity, orm)
        return self._to_domain(orm)

    async def delete(self, entity_id: uuid.UUID) -> None:
        statement = delete(self.model).where(self.model.id == entity_id)
        await self._session.execute(statement)
        # Flush удален; управление транзакцией - в UoW
