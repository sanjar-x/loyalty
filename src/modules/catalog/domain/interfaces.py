# src/modules/catalog/domain/interfaces.py
import uuid
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.entities import Category as DomainCategory

T = TypeVar("T")


class ICatalogRepository(Generic[T], ABC):
    @abstractmethod
    async def add(self, data: T) -> T:
        """Создать новую запись."""
        pass

    @abstractmethod
    async def get(self, id: uuid.UUID) -> T | None:
        """Получить запись по ID."""
        pass

    @abstractmethod
    async def update(self, data: T) -> T:
        """Обновить существующую запись."""
        pass

    @abstractmethod
    async def delete(self, id: uuid.UUID) -> None:
        """Удалить запись."""
        pass


class IBrandRepository(ICatalogRepository[DomainBrand]):
    """Репозиторий брендов."""

    @abstractmethod
    async def check_slug_exists(self, slug: str) -> bool:
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


class IAttributeRepository(ICatalogRepository[Any]):
    """Репозиторий определений атрибутов (EAV)."""

    pass


class IProductRepository(ICatalogRepository[Any]):
    """Репозиторий товаров."""

    pass
