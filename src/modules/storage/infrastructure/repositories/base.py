# src/modules/catalog/infrastructure/repositories/base.py
import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import Result, delete, insert, inspect
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.interfaces import ICatalogRepository
from src.shared.interfaces.entities import IBase

ModelType = TypeVar("ModelType", bound=IBase)


class BaseRepository(Generic[ModelType], ICatalogRepository[ModelType]):
    """
    Высокопроизводительный базовый репозиторий.
    Умеет принимать как ORM-модели, так и сырые словари (dict).
    """

    model: type[ModelType]
    _insertable_keys: frozenset[str]
    _updatable_keys: frozenset[str]

    def __init_subclass__(
        cls, model_class: type[ModelType] | None = None, **kwargs: Any
    ) -> None:
        super().__init_subclass__(**kwargs)
        if model_class:
            cls.model = model_class
            mapper = inspect(model_class)
            valid_columns = {col.key for col in mapper.columns}

            cls._insertable_keys = frozenset(valid_columns)
            cls._updatable_keys = frozenset(valid_columns - {"id", "created_at"})

    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, data: ModelType | dict[str, Any]) -> ModelType:
        if isinstance(data, dict):
            insert_data = {k: v for k, v in data.items() if k in self._insertable_keys}
            statement = insert(self.model).values(insert_data).returning(self.model)
            result = await self._session.execute(statement)
            return result.scalar_one()
        else:
            self._session.add(data)
            await self._session.flush()
            return data

    async def get(self, id: uuid.UUID) -> ModelType | None:
        return await self._session.get(self.model, id)

    async def update(self, data: ModelType | dict[str, Any]) -> ModelType:
        if isinstance(data, dict):
            obj_id = data.get("id")
            if not obj_id:
                raise ValueError("Словарь должен содержать 'id' для обновления.")

            update_data = {k: v for k, v in data.items() if k in self._updatable_keys}
            statement = (
                sa_update(self.model)
                .where(self.model.id == obj_id)
                .values(update_data)
                .returning(self.model)
            )
            result: Result = await self._session.execute(statement)
            return result.scalar_one()
        else:
            await self._session.flush()
            return data

    async def delete(self, id: uuid.UUID) -> None:
        statement = delete(self.model).where(self.model.id == id)
        await self._session.execute(statement)
        await self._session.flush()
