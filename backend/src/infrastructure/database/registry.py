"""ORM model registry for Alembic auto-generation.

Importing this module ensures that all ORM models across every bounded-context
module are registered with the shared ``Base.metadata``, so Alembic's
``--autogenerate`` can detect schema changes.
"""

from src.infrastructure.database.base import Base
from src.infrastructure.database.models.outbox import OutboxMessage
from src.modules.catalog.infrastructure.models import (
    SKU,
    Attribute,
    AttributeValue,
    Brand,
    Category,
    CategoryAttributeRule,
    MediaAsset,
    Product,
    ProductAttributeValueModel,
    SKUAttributeValueLink,
)
from src.modules.geo.infrastructure.models import (
    CountryModel,
    CountryTranslationModel,
    LanguageModel,
    SubdivisionCategoryModel,
    SubdivisionCategoryTranslationModel,
    SubdivisionModel,
    SubdivisionTranslationModel,
)
from src.modules.identity.infrastructure.models import (
    IdentityModel,
    IdentityRoleModel,
    LinkedAccountModel,
    LocalCredentialsModel,
    PermissionModel,
    RoleHierarchyModel,
    RoleModel,
    RolePermissionModel,
    SessionModel,
    SessionRoleModel,
)
from src.modules.user.infrastructure.models import UserModel

__all__ = [
    "SKU",
    "Attribute",
    "AttributeValue",
    "Base",
    "Brand",
    "Category",
    "CategoryAttributeRule",
    "CountryModel",
    "CountryTranslationModel",
    "IdentityModel",
    "IdentityRoleModel",
    "LanguageModel",
    "LinkedAccountModel",
    "LocalCredentialsModel",
    "MediaAsset",
    "OutboxMessage",
    "PermissionModel",
    "Product",
    "ProductAttributeValueModel",
    "RoleHierarchyModel",
    "RoleModel",
    "RolePermissionModel",
    "SKUAttributeValueLink",
    "SessionModel",
    "SessionRoleModel",
    "SubdivisionCategoryModel",
    "SubdivisionCategoryTranslationModel",
    "SubdivisionModel",
    "SubdivisionTranslationModel",
    "UserModel",
]
