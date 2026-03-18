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
    "Base",
    "OutboxMessage",
    # Catalog
    "Brand",
    "Category",
    "Attribute",
    "AttributeValue",
    "CategoryAttributeRule",
    "Product",
    "MediaAsset",
    "SKU",
    "SKUAttributeValueLink",
    "ProductAttributeValueModel",
    # Identity
    "IdentityModel",
    "LocalCredentialsModel",
    "LinkedAccountModel",
    "RoleModel",
    "PermissionModel",
    "RolePermissionModel",
    "RoleHierarchyModel",
    "IdentityRoleModel",
    "SessionModel",
    "SessionRoleModel",
    # User
    "UserModel",
]
