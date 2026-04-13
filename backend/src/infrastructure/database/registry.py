"""ORM model registry for Alembic auto-generation.

Importing this module ensures that all ORM models across every bounded-context
module are registered with the shared ``Base.metadata``, so Alembic's
``--autogenerate`` can detect schema changes.
"""

from src.infrastructure.database.base import Base
from src.infrastructure.database.models.failed_task import FailedTask
from src.infrastructure.database.models.outbox import OutboxMessage
from src.modules.cart.infrastructure.models import (
    CartItemModel,
    CartModel,
    CheckoutAttemptModel,
    CheckoutSnapshotModel,
)
from src.modules.catalog.infrastructure.models import (
    SKU,
    Attribute,
    AttributeGroup,
    AttributeTemplate,
    AttributeValue,
    Brand,
    Category,
    MediaAsset,
    Product,
    ProductAttributeValue,
    ProductVariant,
    SKUAttributeValueLink,
    TemplateAttributeBinding,
)
from src.modules.geo.infrastructure.models import (
    CountryCurrencyModel,
    CountryModel,
    CountryTranslationModel,
    CurrencyModel,
    CurrencyTranslationModel,
    LanguageModel,
    SubdivisionModel,
    SubdivisionTranslationModel,
    SubdivisionTypeModel,
    SubdivisionTypeTranslationModel,
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
from src.modules.logistics.infrastructure.models import (
    DeliveryQuoteModel,
    ProviderAccountModel,
    ShipmentModel,
    ShipmentTrackingEventModel,
)
from src.modules.supplier.infrastructure.models import Supplier
from src.modules.user.infrastructure.models import CustomerModel, StaffMemberModel

__all__ = [
    "SKU",
    "Attribute",
    "AttributeGroup",
    "AttributeTemplate",
    "AttributeValue",
    "Base",
    "Brand",
    "CartItemModel",
    "CartModel",
    "Category",
    "CheckoutAttemptModel",
    "CheckoutSnapshotModel",
    "CountryCurrencyModel",
    "CountryModel",
    "CountryTranslationModel",
    "CurrencyModel",
    "CurrencyTranslationModel",
    "CustomerModel",
    "DeliveryQuoteModel",
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
    "ProviderAccountModel",
    "RoleHierarchyModel",
    "RoleModel",
    "RolePermissionModel",
    "SKUAttributeValueLink",
    "SessionModel",
    "SessionRoleModel",
    "ShipmentModel",
    "ShipmentTrackingEventModel",
    "StaffInvitationModel",
    "StaffInvitationRoleModel",
    "StaffMemberModel",
    "SubdivisionModel",
    "SubdivisionTranslationModel",
    "SubdivisionTypeModel",
    "SubdivisionTypeTranslationModel",
    "Supplier",
    "TemplateAttributeBinding",
]
