# src/modules/catalog/infrastructure/repositories/catalog_repos.py

from src.modules.catalog.domain.interfaces import (
    IProductRepository,
)
from src.modules.catalog.infrastructure.models import (
    Product,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class ProductRepository(
    BaseRepository[Product], IProductRepository, model_class=Product
):
    pass
