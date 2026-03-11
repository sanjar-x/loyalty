# src/modules/catalog/infrastructure/repositories/catalog_repos.py
from sqlalchemy import Sequence, select

from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IBrandRepository,
    ICategoryRepository,
    IProductRepository,
)
from src.modules.catalog.infrastructure.models import (
    Attribute,
    Brand,
    Category,
    Product,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class CategoryRepository(
    BaseRepository[Category], ICategoryRepository, model_class=Category
):
    async def get_all_ordered(self) -> Sequence[Category]:
        statement = select(self.model).order_by(
            self.model.level.asc(), self.model.sort_order.asc()
        )
        result = await self._session.execute(statement)
        return result.scalars().all()


class BrandRepository(BaseRepository[Brand], IBrandRepository, model_class=Brand):
    async def get_by_slug(self, slug: str) -> Brand | None:
        statement = select(self.model).where(self.model.slug == slug)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()


class AttributeRepository(
    BaseRepository[Attribute], IAttributeRepository, model_class=Attribute
):
    """
    Для атрибутов пока хватает базового CRUD (add, get, update, delete),
    который уже реализован в BaseSQLAlchemyRepository.
    """

    pass


class ProductRepository(
    BaseRepository[Product], IProductRepository, model_class=Product
):
    """
    Будущие методы (get_by_slug, get_with_skus) будут добавляться сюда.
    """

    pass
