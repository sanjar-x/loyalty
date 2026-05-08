"""Generic CRUD repository contract — shared kernel (REC-031).

Replaces the catalog-private ``ICatalogRepository[T]`` as the canonical
generic CRUD interface. Modules whose repositories follow the simple
Data-Mapper add/get/update/delete pattern should subclass this; modules
with bespoke read-only or denormalised query surfaces (geo, activity)
keep their custom protocols.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod


class IBaseRepository[T](ABC):
    """Generic CRUD repository contract.

    Type parameter ``T`` is the domain entity (aggregate root) type.
    Module-specific repository protocols extend this and add
    domain-specific query methods.
    """

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Persist a new aggregate and return it with any generated fields."""

    @abstractmethod
    async def get(self, entity_id: uuid.UUID) -> T | None:
        """Retrieve an aggregate by its unique identifier."""

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Persist changes to an existing aggregate."""

    @abstractmethod
    async def delete(self, entity_id: uuid.UUID) -> None:
        """Delete an aggregate by its unique identifier."""
