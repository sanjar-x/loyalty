# src/modules/catalog/domain/interfaces.py
import uuid
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.entities import Category as DomainCategory

T = TypeVar("T")


class ICatalogRepository(Generic[T], ABC):
    @abstractmethod
    async def add(self, entity: T) -> T:
        """Создать новую запись."""
        pass

    @abstractmethod
    async def get(self, entity_id: uuid.UUID) -> T | None:
        """Получить запись по ID."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Обновить существующую запись."""
        pass

    @abstractmethod
    async def delete(self, entity_id: uuid.UUID) -> None:
        """Удалить запись."""
        pass


class IBrandRepository(ICatalogRepository[DomainBrand]):
    """Репозиторий брендов."""

    @abstractmethod
    async def check_slug_exists(self, slug: str) -> bool:
        pass

    @abstractmethod
    async def get_for_update(self, brand_id: uuid.UUID) -> DomainBrand | None:
        """Получить бренд с пессимистической блокировкой (SELECT FOR UPDATE)."""
        pass

    @abstractmethod
    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        """Check if slug is taken by another brand (excluding given ID)."""
        pass


class ICategoryRepository(ICatalogRepository[DomainCategory]):
    """Репозиторий категорий."""

    @abstractmethod
    async def get_all_ordered(self) -> list[DomainCategory]:
        """Получить иерархическое дерево категорий."""
        pass

    @abstractmethod
    async def check_slug_exists(self, slug: str, parent_id: uuid.UUID | None) -> bool:
        pass

    @abstractmethod
    async def get_for_update(self, category_id: uuid.UUID) -> DomainCategory | None:
        """Получить категорию с пессимистической блокировкой (SELECT FOR UPDATE)."""
        pass

    @abstractmethod
    async def check_slug_exists_excluding(
        self, slug: str, parent_id: uuid.UUID | None, exclude_id: uuid.UUID
    ) -> bool:
        """Check if slug is taken by another category at the same parent level."""
        pass

    @abstractmethod
    async def has_children(self, category_id: uuid.UUID) -> bool:
        """Check if category has any child categories."""
        pass

    @abstractmethod
    async def update_descendants_full_slug(self, old_prefix: str, new_prefix: str) -> None:
        """Bulk-update full_slug for all descendants when a parent's slug changes."""
        pass


class IAttributeRepository(ICatalogRepository[Any]):
    """Репозиторий определений атрибутов (EAV)."""

    pass


class IProductRepository(ICatalogRepository[Any]):
    """Репозиторий товаров."""

    pass
