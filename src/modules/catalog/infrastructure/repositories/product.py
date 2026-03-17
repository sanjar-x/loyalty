"""
Product repository — placeholder Data Mapper implementation.

Currently returns raw ORM instances because the domain Product entity
has not been implemented yet.  Replace ``Any`` with a proper domain
model once the Product aggregate is built out.
"""

from typing import Any

from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.infrastructure.models import Product
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Any, Product], IProductRepository, model_class=Product):
    """Placeholder repository for products.

    Uses ``Any`` as the domain type because the Product domain entity
    has not been implemented yet.  Mapping methods are stubs.
    """

    def _to_domain(self, orm: Product) -> Any:
        """Return the ORM instance as-is (no domain entity exists yet)."""
        return orm

    def _to_orm(self, entity: Any, orm: Product | None = None) -> Product:
        """Return a bare ORM instance (no domain mapping exists yet)."""
        if orm is None:
            orm = Product()
        return orm
