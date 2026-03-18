"""
Catalog repository port interfaces.

Defines the abstract repository contracts for Brand, Category, Product,
Attribute, and AttributeGroup aggregates. The application layer depends
only on these interfaces; concrete implementations live in the
infrastructure layer.

Typical usage:
    class CreateBrandHandler:
        def __init__(self, repo: IBrandRepository) -> None:
            self._repo = repo
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from src.modules.catalog.domain.entities import Attribute as DomainAttribute
from src.modules.catalog.domain.entities import AttributeGroup
from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.entities import Category as DomainCategory

T = TypeVar("T")


class ICatalogRepository(Generic[T], ABC):
    """Generic CRUD repository contract for catalog aggregates.

    Type parameter ``T`` is the domain entity type (e.g. ``DomainBrand``).
    Module-specific repositories extend this with additional query methods.
    """

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Persist a new aggregate and return it with any generated fields."""
        pass

    @abstractmethod
    async def get(self, entity_id: uuid.UUID) -> T | None:
        """Retrieve an aggregate by its unique identifier."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Persist changes to an existing aggregate."""
        pass

    @abstractmethod
    async def delete(self, entity_id: uuid.UUID) -> None:
        """Remove an aggregate by its unique identifier."""
        pass


class IBrandRepository(ICatalogRepository[DomainBrand]):
    """Repository contract for the Brand aggregate."""

    @abstractmethod
    async def check_slug_exists(self, slug: str) -> bool:
        """Check whether a brand with the given slug already exists."""
        pass

    @abstractmethod
    async def get_for_update(self, brand_id: uuid.UUID) -> DomainBrand | None:
        """Retrieve a brand with a pessimistic lock (SELECT FOR UPDATE)."""
        pass

    @abstractmethod
    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        """Check if a slug is taken by another brand (excluding given ID)."""
        pass


class ICategoryRepository(ICatalogRepository[DomainCategory]):
    """Repository contract for the Category aggregate."""

    @abstractmethod
    async def get_all_ordered(self) -> list[DomainCategory]:
        """Retrieve the full category tree ordered by level and sort_order."""
        pass

    @abstractmethod
    async def check_slug_exists(self, slug: str, parent_id: uuid.UUID | None) -> bool:
        """Check whether a category slug exists at the given parent level."""
        pass

    @abstractmethod
    async def get_for_update(self, category_id: uuid.UUID) -> DomainCategory | None:
        """Retrieve a category with a pessimistic lock (SELECT FOR UPDATE)."""
        pass

    @abstractmethod
    async def check_slug_exists_excluding(
        self, slug: str, parent_id: uuid.UUID | None, exclude_id: uuid.UUID
    ) -> bool:
        """Check if a slug is taken by another category at the same level."""
        pass

    @abstractmethod
    async def has_children(self, category_id: uuid.UUID) -> bool:
        """Check whether a category has any child categories."""
        pass

    @abstractmethod
    async def update_descendants_full_slug(self, old_prefix: str, new_prefix: str) -> None:
        """Bulk-update full_slug for all descendants when a parent's slug changes."""
        pass


class IAttributeGroupRepository(ICatalogRepository[AttributeGroup]):
    """Repository contract for the AttributeGroup aggregate."""

    @abstractmethod
    async def check_code_exists(self, code: str) -> bool:
        """Check whether a group with the given code already exists."""
        pass

    @abstractmethod
    async def get_by_code(self, code: str) -> AttributeGroup | None:
        """Retrieve an attribute group by its unique code."""
        pass

    @abstractmethod
    async def has_attributes(self, group_id: uuid.UUID) -> bool:
        """Check whether the group contains any attributes."""
        pass

    @abstractmethod
    async def move_attributes_to_group(
        self, source_group_id: uuid.UUID, target_group_id: uuid.UUID
    ) -> None:
        """Bulk-move all attributes from one group to another."""
        pass


class IAttributeRepository(ICatalogRepository[DomainAttribute]):
    """Repository contract for the Attribute aggregate."""

    @abstractmethod
    async def check_code_exists(self, code: str) -> bool:
        """Check whether an attribute with the given code already exists."""
        pass

    @abstractmethod
    async def check_slug_exists(self, slug: str) -> bool:
        """Check whether an attribute with the given slug already exists."""
        pass

    @abstractmethod
    async def check_code_exists_excluding(self, code: str, exclude_id: uuid.UUID) -> bool:
        """Check if a code is taken by another attribute (excluding given ID)."""
        pass

    @abstractmethod
    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        """Check if a slug is taken by another attribute (excluding given ID)."""
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> DomainAttribute | None:
        """Retrieve an attribute by its URL slug."""
        pass

    @abstractmethod
    async def has_category_bindings(self, attribute_id: uuid.UUID) -> bool:
        """Check whether the attribute is bound to at least one category."""
        pass


class IProductRepository(ICatalogRepository[Any]):
    """Repository contract for the Product aggregate."""

    pass
