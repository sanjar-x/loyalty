from src.modules.catalog.infrastructure.repositories.attribute import (
    AttributeRepository,
)
from src.modules.catalog.infrastructure.repositories.attribute_group import (
    AttributeGroupRepository,
)
from src.modules.catalog.infrastructure.repositories.attribute_template import (
    AttributeTemplateRepository,
)
from src.modules.catalog.infrastructure.repositories.attribute_value import (
    AttributeValueRepository,
)
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository
from src.modules.catalog.infrastructure.repositories.category import CategoryRepository
from src.modules.catalog.infrastructure.repositories.media_asset import (
    MediaAssetRepository,
)
from src.modules.catalog.infrastructure.repositories.product import ProductRepository
from src.modules.catalog.infrastructure.repositories.product_attribute_value import (
    ProductAttributeValueRepository,
)
from src.modules.catalog.infrastructure.repositories.template_attribute_binding import (
    TemplateAttributeBindingRepository,
)

__all__ = [
    "AttributeGroupRepository",
    "AttributeRepository",
    "AttributeTemplateRepository",
    "AttributeValueRepository",
    "BrandRepository",
    "CategoryRepository",
    "MediaAssetRepository",
    "ProductAttributeValueRepository",
    "ProductRepository",
    "TemplateAttributeBindingRepository",
]
