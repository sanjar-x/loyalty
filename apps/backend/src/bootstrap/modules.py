"""Single source of truth for the list of bounded-context modules.

Adding a new module is a two-step change:

1. Create ``src/modules/<name>/module.py`` exposing a
   :class:`ModuleManifest` constant.
2. Append it to :data:`MODULES` below.

Every consumer of the registry — DI container, FastAPI router
aggregation, TaskIQ worker / scheduler bootstrap, integration-test
container — iterates :data:`MODULES`. There is no other place a new
module needs to be registered.
"""

from __future__ import annotations

from src.bootstrap.module_registry import ModuleManifest
from src.modules.activity.module import ACTIVITY_MODULE
from src.modules.cart.module import CART_MODULE
from src.modules.catalog.module import CATALOG_MODULE
from src.modules.favorites.module import FAVORITES_MODULE
from src.modules.geo.module import GEO_MODULE
from src.modules.identity.module import IDENTITY_MODULE
from src.modules.image.module import IMAGE_MODULE
from src.modules.logistics.module import LOGISTICS_MODULE
from src.modules.order.module import ORDER_MODULE
from src.modules.passport.module import PASSPORT_MODULE
from src.modules.payment.module import PAYMENT_MODULE
from src.modules.pricing.module import PRICING_MODULE
from src.modules.recipient.module import RECIPIENT_MODULE
from src.modules.referral.module import REFERRAL_MODULE
from src.modules.supplier.module import SUPPLIER_MODULE
from src.modules.user.module import USER_MODULE

# Ordered: cross-module references resolve in declaration order at
# container assembly. Identity is first among the business modules
# because every other module's admin endpoints depend on its
# ``RequirePermission`` dependency. Reference data (geo) follows.
# Catalog precedes pricing so that pricing's CQRS read-side can
# resolve catalog ORM models registered upstream.
#
# Referral lands last — it consumes identity events (IdentityRegistered /
# LinkedAccountCreated) via the outbox, owns the loyalty wallet that the
# shared ledger kernel (PR-6a) backs, and ships its first concrete
# ILedger consumer (SqlLoyaltyLedger) as the pattern reference for any
# future ledger consumer (cashback, supplier payouts, refund pool).
MODULES: tuple[ModuleManifest, ...] = (
    GEO_MODULE,
    IDENTITY_MODULE,
    USER_MODULE,
    SUPPLIER_MODULE,
    CATALOG_MODULE,
    PRICING_MODULE,
    ACTIVITY_MODULE,
    CART_MODULE,
    FAVORITES_MODULE,
    IMAGE_MODULE,
    LOGISTICS_MODULE,
    PAYMENT_MODULE,
    RECIPIENT_MODULE,
    # Passport is registered right after Recipient because both are
    # customer-PII bounded contexts; Order (next) depends on both via
    # IRecipientLookup + IPassportLookup adapters but reads passports
    # at request time, not at manifest discovery — order so the DI
    # container has both providers when order's request handlers fire.
    PASSPORT_MODULE,
    ORDER_MODULE,
    REFERRAL_MODULE,
)
