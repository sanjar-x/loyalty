"""
Base repository implementing the Data Mapper pattern for catalog aggregates.

Provides generic CRUD operations that convert between SQLAlchemy ORM models
and domain entities.  Concrete repositories inherit from :class:`BaseRepository`
and supply the ``_to_domain`` / ``_to_orm`` mapping methods.

Note:
    Most catalog repositories inherit this base class.
    ``ProductRepository`` and ``MediaAssetRepository`` remain standalone
    implementations due to their specialised query requirements.
"""

import uuid
from abc import abstractmethod
from typing import Any

from sqlalchemy import ColumnElement, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.interfaces import ICatalogRepository
from src.shared.exceptions import NotFoundError
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

    def __init__(self, session: AsyncSession) -> None:
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
        await self._session.flush()
        return self._to_domain(orm)

    async def get_or_raise(
        self,
        entity_id: uuid.UUID,
        error: NotFoundError | None = None,
    ) -> EntityType:
        """Retrieve a domain entity by primary key, raising if not found.

        Convenience wrapper around :meth:`get` that eliminates the
        repetitive ``fetch → check None → raise`` pattern in command
        handlers.

        Args:
            entity_id: Primary key of the entity to fetch.
            error: A pre-built ``NotFoundError`` to raise when the entity
                is missing.  When ``None`` a generic ``NotFoundError`` is
                used instead.

        Raises:
            NotFoundError: If the entity does not exist.
        """
        entity = await self.get(entity_id)
        if entity is None:
            raise error or NotFoundError(
                message=f"{self.model.__name__} with id {entity_id} not found",
            )
        return entity

    async def _field_exists(
        self,
        field_name: str,
        value: Any,
        *,
        exclude_id: uuid.UUID | None = None,
        extra_filters: list[ColumnElement[bool]] | None = None,
    ) -> bool:
        """Check whether a row with the given field value already exists.

        Generic helper that replaces per-repository ``check_slug_exists``
        and ``check_slug_exists_excluding`` boilerplate.

        Args:
            field_name: Name of the ORM column to check (e.g. ``"slug"``).
            value: The value to look for.
            exclude_id: When provided, excludes the row with this primary
                key from the check (used during updates).
            extra_filters: Additional SQLAlchemy column expressions that
                are ANDed into the query (e.g.
                ``[Model.parent_id == parent_id]``).

        Returns:
            ``True`` if a matching row exists, ``False`` otherwise.
        """
        column = getattr(self.model, field_name)
        filters: list[ColumnElement[bool]] = [column == value]
        if exclude_id is not None:
            filters.append(self.model.id != exclude_id)
        if extra_filters:
            filters.extend(extra_filters)
        stmt = select(self.model.id).where(*filters).limit(1)
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def delete(self, entity_id: uuid.UUID) -> None:
        """Delete a row by primary key.  Transaction control is in the UoW."""
        stmt = delete(self.model).where(self.model.id == entity_id)
        await self._session.execute(stmt)
