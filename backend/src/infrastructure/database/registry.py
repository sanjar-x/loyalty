"""ORM model registry for Alembic auto-generation.

Importing this module ensures that all ORM models across every bounded-context
module are registered with the shared ``Base.metadata``, so Alembic's
``--autogenerate`` can detect schema changes.
"""

from src.infrastructure.database.base import Base
from src.infrastructure.database.models.failed_task import FailedTask
from src.infrastructure.database.models.outbox import OutboxMessage
from src.modules.catalog.infrastructure.models import (
    SKU,
    Attribute,
    AttributeGroup,
    AttributeValue,
    Brand,
    Category,
    CategoryAttributeBinding,
    MediaAsset,
    Product,
    ProductAttributeValue,
    ProductVariant,
    SKUAttributeValueLink,
)
from src.modules.geo.infrastructure.models import (
    CountryCurrencyModel,
    CountryModel,
    CountryTranslationModel,
    CurrencyModel,
    CurrencyTranslationModel,
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
    StaffInvitationModel,
    StaffInvitationRoleModel,
)
from src.modules.storage.infrastructure.models import StorageObject
from src.modules.supplier.infrastructure.models import Supplier
from src.modules.user.infrastructure.models import CustomerModel, StaffMemberModel

__all__ = [
    "SKU",
    "Attribute",
    "AttributeGroup",
    "AttributeValue",
    "Base",
    "Brand",
    "Category",
    "CategoryAttributeBinding",
    "CountryCurrencyModel",
    "CountryModel",
    "CountryTranslationModel",
    "CurrencyModel",
    "CurrencyTranslationModel",
    "CustomerModel",
    "FailedTask",
    "IdentityModel",
    "IdentityRoleModel",
    "LanguageModel",
    "LinkedAccountModel",
    "LocalCredentialsModel",
    "MediaAsset",
    "OutboxMessage",
    "PermissionModel",
    "Product",
    "ProductAttributeValue",
    "ProductVariant",
    "RoleHierarchyModel",
    "RoleModel",
    "RolePermissionModel",
    "SKUAttributeValueLink",
    "SessionModel",
    "SessionRoleModel",
    "StaffInvitationModel",
    "StaffInvitationRoleModel",
    "StaffMemberModel",
    "StorageObject",
    "Supplier",
    "SubdivisionCategoryModel",
    "SubdivisionCategoryTranslationModel",
    "SubdivisionModel",
    "SubdivisionTranslationModel",
]
