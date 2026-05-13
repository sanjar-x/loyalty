# tests/factories/orm_factories.py
"""Polyfactory-based ORM model factories for integration test data seeding."""

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from src.modules.catalog.infrastructure.models import (
    SKU as SKUModel,
)
from src.modules.catalog.infrastructure.models import (
    Attribute as AttributeModel,
)
from src.modules.catalog.infrastructure.models import (
    AttributeGroup as AttributeGroupModel,
)
from src.modules.catalog.infrastructure.models import (
    AttributeTemplate as AttributeTemplateModel,
)
from src.modules.catalog.infrastructure.models import (
    AttributeValue as AttributeValueModel,
)
from src.modules.catalog.infrastructure.models import (
    Brand as BrandModel,
)
from src.modules.catalog.infrastructure.models import (
    Category as CategoryModel,
)
from src.modules.catalog.infrastructure.models import (
    MediaAsset as MediaAssetModel,
)
from src.modules.catalog.infrastructure.models import (
    Product as ProductModel,
)
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValue as ProductAttributeValueModel,
)
from src.modules.catalog.infrastructure.models import (
    ProductVariant as ProductVariantModel,
)
from src.modules.catalog.infrastructure.models import (
    SKUAttributeValueLink as SKUAttributeValueLinkModel,
)
from src.modules.catalog.infrastructure.models import (
    TemplateAttributeBinding as TemplateAttributeBindingModel,
)
from src.modules.identity.infrastructure.models import (
    IdentityModel,
    LocalCredentialsModel,
    RoleModel,
    SessionModel,
)

# ---------------------------------------------------------------------------
# Identity module ORM factories
# ---------------------------------------------------------------------------


class IdentityModelFactory(SQLAlchemyFactory):
    __model__ = IdentityModel
    __set_relationships__ = True


class CredentialsModelFactory(SQLAlchemyFactory):
    __model__ = LocalCredentialsModel
    __set_relationships__ = True


class SessionModelFactory(SQLAlchemyFactory):
    __model__ = SessionModel
    __set_relationships__ = True


class RoleModelFactory(SQLAlchemyFactory):
    __model__ = RoleModel
    __set_relationships__ = True


# ---------------------------------------------------------------------------
# Catalog module ORM factories
# ---------------------------------------------------------------------------


class BrandModelFactory(SQLAlchemyFactory):
    __model__ = BrandModel
    __set_relationships__ = True


class CategoryModelFactory(SQLAlchemyFactory):
    __model__ = CategoryModel
    __set_relationships__ = True


class AttributeTemplateModelFactory(SQLAlchemyFactory):
    __model__ = AttributeTemplateModel
    __set_relationships__ = True


class AttributeGroupModelFactory(SQLAlchemyFactory):
    __model__ = AttributeGroupModel
    __set_relationships__ = True


class AttributeModelFactory(SQLAlchemyFactory):
    __model__ = AttributeModel
    __set_relationships__ = True


class AttributeValueModelFactory(SQLAlchemyFactory):
    __model__ = AttributeValueModel
    __set_relationships__ = True


class TemplateAttributeBindingModelFactory(SQLAlchemyFactory):
    __model__ = TemplateAttributeBindingModel
    __set_relationships__ = True


class ProductModelFactory(SQLAlchemyFactory):
    __model__ = ProductModel
    __set_relationships__ = True


class ProductVariantModelFactory(SQLAlchemyFactory):
    __model__ = ProductVariantModel
    __set_relationships__ = True


class SKUModelFactory(SQLAlchemyFactory):
    __model__ = SKUModel
    __set_relationships__ = True


class SKUAttributeValueLinkModelFactory(SQLAlchemyFactory):
    __model__ = SKUAttributeValueLinkModel
    __set_relationships__ = True


class MediaAssetModelFactory(SQLAlchemyFactory):
    __model__ = MediaAssetModel
    __set_relationships__ = True


class ProductAttributeValueModelFactory(SQLAlchemyFactory):
    __model__ = ProductAttributeValueModel
    __set_relationships__ = True
