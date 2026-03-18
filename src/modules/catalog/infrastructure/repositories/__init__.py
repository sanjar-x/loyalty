from src.modules.catalog.infrastructure.repositories.attribute import (
    AttributeRepository,
)
from src.modules.catalog.infrastructure.repositories.attribute_group import (
    AttributeGroupRepository,
)
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository
from src.modules.catalog.infrastructure.repositories.category import CategoryRepository
from src.modules.catalog.infrastructure.repositories.product import ProductRepository

__all__ = [
    "AttributeGroupRepository",
    "AttributeRepository",
    "BrandRepository",
    "CategoryRepository",
    "ProductRepository",
]
