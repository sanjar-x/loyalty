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

    def __init_subclass__(
        cls, model_class: type[ModelType] | None = None, **kwargs: Any
    ) -> None:
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

    async def add(self, data: EntityType) -> EntityType:
        orm = self._to_orm(data)
        self._session.add(orm)
        # Flush нужен только для получения БД-идентификаторов (PK) до коммита
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, id: uuid.UUID) -> EntityType | None:
        orm = await self._session.get(self.model, id)
        if orm:
            return self._to_domain(orm)
        return None

    async def update(self, data: EntityType) -> EntityType:
        entity_id = getattr(data, "id", None)
        if not entity_id:
            raise ValueError("Для обновления у доменной сущности должен быть id")

        orm = await self._session.get(self.model, entity_id)
        if not orm:
            raise ValueError(f"Сущность с id {entity_id} не найдена в БД")

        orm = self._to_orm(data, orm)
        return self._to_domain(orm)

    async def delete(self, id: uuid.UUID) -> None:
        statement = delete(self.model).where(self.model.id == id)
        await self._session.execute(statement)
        # Flush удален; управление транзакцией - в UoW
