"""
Catalog repository port interfaces.

Defines the abstract repository contracts for Brand, Category, Product,
and Attribute aggregates. The application layer depends only on these
interfaces; concrete implementations live in the infrastructure layer.

Typical usage:
    class CreateBrandHandler:
        def __init__(self, repo: IBrandRepository) -> None:
            self._repo = repo
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

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
        """Persist a new aggregate and return it with any generated fields.

        Args:
            entity: Domain entity to persist.

        Returns:
            The persisted entity.
        """
        pass

    @abstractmethod
    async def get(self, entity_id: uuid.UUID) -> T | None:
        """Retrieve an aggregate by its unique identifier.

        Args:
            entity_id: UUID of the entity.

        Returns:
            The domain entity, or None if not found.
        """
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Persist changes to an existing aggregate.

        Args:
            entity: Domain entity with updated fields.

        Returns:
            The updated entity.
        """
        pass

    @abstractmethod
    async def delete(self, entity_id: uuid.UUID) -> None:
        """Remove an aggregate by its unique identifier.

        Args:
            entity_id: UUID of the entity to delete.
        """
        pass


class IBrandRepository(ICatalogRepository[DomainBrand]):
    """Repository contract for the Brand aggregate."""

    @abstractmethod
    async def check_slug_exists(self, slug: str) -> bool:
        """Check whether a brand with the given slug already exists.

        Args:
            slug: URL-safe slug to check.

        Returns:
            True if a brand with this slug exists.
        """
        pass

    @abstractmethod
    async def get_for_update(self, brand_id: uuid.UUID) -> DomainBrand | None:
        """Retrieve a brand with a pessimistic lock (SELECT FOR UPDATE).

        Args:
            brand_id: UUID of the brand.

        Returns:
            The locked domain entity, or None if not found.
        """
        pass

    @abstractmethod
    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        """Check if a slug is taken by another brand (excluding given ID).

        Args:
            slug: URL-safe slug to check.
            exclude_id: Brand ID to exclude from the check.

        Returns:
            True if another brand holds this slug.
        """
        pass


class ICategoryRepository(ICatalogRepository[DomainCategory]):
    """Repository contract for the Category aggregate."""

    @abstractmethod
    async def get_all_ordered(self) -> list[DomainCategory]:
        """Retrieve the full category tree ordered by level and sort_order.

        Returns:
            Flat list of all categories in hierarchical display order.
        """
        pass

    @abstractmethod
    async def check_slug_exists(self, slug: str, parent_id: uuid.UUID | None) -> bool:
        """Check whether a category slug exists at the given parent level.

        Args:
            slug: URL-safe slug to check.
            parent_id: Parent category UUID, or None for root level.

        Returns:
            True if a category with this slug exists at this level.
        """
        pass

    @abstractmethod
    async def get_for_update(self, category_id: uuid.UUID) -> DomainCategory | None:
        """Retrieve a category with a pessimistic lock (SELECT FOR UPDATE).

        Args:
            category_id: UUID of the category.

        Returns:
            The locked domain entity, or None if not found.
        """
        pass

    @abstractmethod
    async def check_slug_exists_excluding(
        self, slug: str, parent_id: uuid.UUID | None, exclude_id: uuid.UUID
    ) -> bool:
        """Check if a slug is taken by another category at the same level.

        Args:
            slug: URL-safe slug to check.
            parent_id: Parent category UUID, or None for root level.
            exclude_id: Category ID to exclude from the check.

        Returns:
            True if another category holds this slug at this level.
        """
        pass

    @abstractmethod
    async def has_children(self, category_id: uuid.UUID) -> bool:
        """Check whether a category has any child categories.

        Args:
            category_id: UUID of the category.

        Returns:
            True if at least one child category exists.
        """
        pass

    @abstractmethod
    async def update_descendants_full_slug(self, old_prefix: str, new_prefix: str) -> None:
        """Bulk-update full_slug for all descendants when a parent's slug changes.

        Args:
            old_prefix: The previous full_slug prefix to match.
            new_prefix: The new full_slug prefix to replace with.
        """
        pass


class IAttributeRepository(ICatalogRepository[Any]):
    """Repository contract for attribute definitions (EAV schema)."""

    pass


class IProductRepository(ICatalogRepository[Any]):
    """Repository contract for the Product aggregate."""

    pass
