"""
Catalog domain entities package.

Re-exports all public entity classes and constants for backward compatibility.
All existing import sites (68+) use:
    from src.modules.catalog.domain.entities import Brand
This __init__.py ensures those imports continue working after the file split.
"""

from ._common import GENERAL_GROUP_CODE
from .attribute import Attribute
from .attribute_group import AttributeGroup
from .attribute_template import AttributeTemplate
from .attribute_value import AttributeValue
from .brand import Brand
from .category import Category, MAX_CATEGORY_DEPTH
from .media_asset import MediaAsset
from .product import Product
from .product_attribute_value import ProductAttributeValue
from .product_variant import ProductVariant
from .sku import SKU
from .template_attribute_binding import TemplateAttributeBinding

__all__ = [
    "Attribute",
    "AttributeGroup",
    "AttributeTemplate",
    "AttributeValue",
    "Brand",
    "Category",
    "GENERAL_GROUP_CODE",
    "MAX_CATEGORY_DEPTH",
    "MediaAsset",
    "Product",
    "ProductAttributeValue",
    "ProductVariant",
    "SKU",
    "TemplateAttributeBinding",
]
