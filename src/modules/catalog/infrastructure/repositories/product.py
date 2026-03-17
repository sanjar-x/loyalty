# src/modules/catalog/infrastructure/repositories/product.py
from typing import Any

from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.infrastructure.models import Product
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Any, Product], IProductRepository, model_class=Product):
    def _to_domain(self, orm: Product) -> Any:
        return orm

    def _to_orm(self, entity: Any, orm: Product | None = None) -> Product:
        if orm is None:
            orm = Product()
        return orm
