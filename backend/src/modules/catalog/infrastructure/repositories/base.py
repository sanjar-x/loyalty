"""
Base repository implementing the Data Mapper pattern for catalog aggregates.

Provides generic CRUD operations that convert between SQLAlchemy ORM models
and domain entities.  Concrete repositories inherit from :class:`BaseRepository`
and supply the ``_to_domain`` / ``_to_orm`` mapping methods.
"""

import uuid
from abc import abstractmethod
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.interfaces import ICatalogRepository
from src.shared.interfaces.entities import IBase


class BaseRepository[EntityType, ModelType: IBase](ICatalogRepository[EntityType]):
    """Generic Data Mapper repository.

    Accepts and returns only domain entities (``EntityType``).
    Subclasses declare the ORM model via the ``model_class`` class argument
    and implement the ``_to_domain`` / ``_to_orm`` mapping hooks.

    Args:
        session: SQLAlchemy async session scoped to the current request.
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
        """Convert an ORM model instance to a domain entity."""

    @abstractmethod
    def _to_orm(self, entity: EntityType, orm: ModelType | None = None) -> ModelType:
        """Convert a domain entity to an ORM model instance.

        Args:
            entity: Domain entity to map.
            orm: Existing ORM instance to update in-place, or ``None``
                to create a new one.
        """

    async def add(self, entity: EntityType) -> EntityType:
        """Persist a new domain entity and return the refreshed copy."""
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, entity_id: uuid.UUID) -> EntityType | None:
        """Retrieve a domain entity by primary key, or ``None``."""
        orm = await self._session.get(self.model, entity_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def update(self, entity: EntityType) -> EntityType:
        """Merge updated domain state into the corresponding ORM row.

        Raises:
            ValueError: If the entity has no ``id`` or the row is missing.
        """
        pk = getattr(entity, "id", None)
        if not pk:
            raise ValueError("Domain entity must have an id for updates")

        orm = await self._session.get(self.model, pk)
        if not orm:
            raise ValueError(f"Entity with id {pk} not found in the database")

        orm = self._to_orm(entity, orm)
        return self._to_domain(orm)

    async def delete(self, entity_id: uuid.UUID) -> None:
        """Delete a row by primary key.  Transaction control is in the UoW."""
        statement = delete(self.model).where(self.model.id == entity_id)
        await self._session.execute(statement)
