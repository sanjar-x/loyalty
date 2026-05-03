"""Root API router that aggregates all module-level routers.

Each bounded-context module exposes routers from its ``presentation/`` layer.
This file groups every ``include_router`` into one of three audiences,
matching the URL convention documented in
``docs/api/router-restructure-2026-05.md`` and enforced by
``tests/architecture/test_router_audience.py``:

* **Customer App** — `/api/v1/<resource>` (storefront, cart, orders, ...).
* **Admin Panel**  — `/api/v1/admin/<module>/<resource>` (staff-only).
* **Webhooks**     — `/api/v1/webhooks/<provider>` (server-to-server).

The router itself defines the full prefix, so ``include_router`` here MUST
NOT pass ``prefix=...`` — that would double-namespace the URL.
"""

from fastapi import APIRouter

# ---------------------------------------------------------------------------
# Admin Panel routers (/admin/* prefix)
# ---------------------------------------------------------------------------
from src.modules.activity.presentation.router_admin import activity_admin_router

# ---------------------------------------------------------------------------
# Customer App routers (no /admin prefix)
# ---------------------------------------------------------------------------
from src.modules.cart.presentation.router_customer import cart_router
from src.modules.catalog.presentation.router_admin_attribute_groups import (
    attribute_group_router,
)
from src.modules.catalog.presentation.router_admin_attribute_templates import (
    attribute_template_router,
)
from src.modules.catalog.presentation.router_admin_attribute_values import (
    attribute_value_router,
)
from src.modules.catalog.presentation.router_admin_attributes import attribute_router
from src.modules.catalog.presentation.router_admin_brands import brand_router
from src.modules.catalog.presentation.router_admin_categories import category_router
from src.modules.catalog.presentation.router_admin_media import media_router
from src.modules.catalog.presentation.router_admin_product_attributes import (
    product_attribute_router,
)
from src.modules.catalog.presentation.router_admin_products import product_router
from src.modules.catalog.presentation.router_admin_skus import sku_router
from src.modules.catalog.presentation.router_admin_variants import variant_router
from src.modules.catalog.presentation.router_storefront import storefront_router
from src.modules.catalog.presentation.router_storefront_for_you import (
    storefront_for_you_router,
)
from src.modules.catalog.presentation.router_storefront_products import (
    storefront_products_router,
)
from src.modules.catalog.presentation.router_storefront_search import (
    storefront_search_router,
)
from src.modules.catalog.presentation.router_storefront_taxonomy import (
    storefront_taxonomy_router,
)
from src.modules.catalog.presentation.router_storefront_trending import (
    storefront_trending_router,
)
from src.modules.favorites.presentation.router_favorites import favorite_router
from src.modules.geo.presentation.router_admin import geo_admin_router
from src.modules.geo.presentation.router_geo import geo_router
from src.modules.identity.presentation.router_account import identity_account_router
from src.modules.identity.presentation.router_admin import admin_router
from src.modules.identity.presentation.router_auth import auth_router
from src.modules.identity.presentation.router_customers import customer_admin_router
from src.modules.identity.presentation.router_invitation import invitation_router
from src.modules.identity.presentation.router_staff import staff_admin_router
from src.modules.logistics.presentation.router_admin import logistics_admin_router
from src.modules.logistics.presentation.router_admin_shipments import (
    logistics_router as logistics_admin_shipments_router,
)
from src.modules.logistics.presentation.router_storefront import (
    logistics_storefront_router,
)

# ---------------------------------------------------------------------------
# Webhook routers (/webhooks/* prefix, server-to-server)
# ---------------------------------------------------------------------------
from src.modules.logistics.presentation.router_webhooks import webhook_router
from src.modules.order.presentation.router_admin import admin_order_router
from src.modules.order.presentation.router_orders import order_router
from src.modules.order.presentation.router_webhooks import dobropost_webhook_router
from src.modules.payment.presentation.router_payments import payment_router
from src.modules.payment.presentation.router_webhooks import payment_webhook_router
from src.modules.pricing.presentation.router_admin_categories import (
    pricing_category_settings_router,
)
from src.modules.pricing.presentation.router_admin_contexts import (
    pricing_context_router,
)
from src.modules.pricing.presentation.router_admin_formulas import (
    pricing_formula_router,
)
from src.modules.pricing.presentation.router_admin_preview import (
    pricing_preview_router,
)
from src.modules.pricing.presentation.router_admin_products import (
    pricing_profile_router,
)
from src.modules.pricing.presentation.router_admin_recompute import (
    pricing_recompute_router,
)
from src.modules.pricing.presentation.router_admin_supplier_type_mapping import (
    pricing_supplier_type_mapping_router,
)
from src.modules.pricing.presentation.router_admin_suppliers import (
    pricing_supplier_settings_router,
)
from src.modules.pricing.presentation.router_admin_variables import (
    pricing_variable_router,
)
from src.modules.recipient.presentation.router_recipients import recipient_router
from src.modules.supplier.presentation.router_admin import supplier_admin_router
from src.modules.user.presentation.router_profile import profile_router

router = APIRouter()

# === Customer App ===
router.include_router(auth_router)
router.include_router(invitation_router)
router.include_router(identity_account_router)
router.include_router(profile_router)
router.include_router(geo_router)
router.include_router(storefront_router)
router.include_router(storefront_taxonomy_router)
router.include_router(storefront_products_router)
router.include_router(storefront_search_router)
router.include_router(storefront_trending_router)
router.include_router(storefront_for_you_router)
router.include_router(logistics_storefront_router)
router.include_router(cart_router)
router.include_router(favorite_router)
router.include_router(order_router)
router.include_router(payment_router)
router.include_router(recipient_router)

# === Admin Panel ===
# Identity & access (root admin namespace at /admin)
router.include_router(admin_router)
router.include_router(staff_admin_router)
router.include_router(customer_admin_router)
# Catalog admin (/admin/catalog/*)
router.include_router(brand_router)
router.include_router(category_router)
router.include_router(attribute_router)
router.include_router(attribute_group_router)
router.include_router(attribute_value_router)
router.include_router(attribute_template_router)
router.include_router(product_router)
router.include_router(variant_router)
router.include_router(sku_router)
router.include_router(product_attribute_router)
router.include_router(media_router)
# Pricing admin (/admin/pricing/*)
router.include_router(pricing_variable_router)
router.include_router(pricing_context_router)
router.include_router(pricing_formula_router)
router.include_router(pricing_preview_router)
router.include_router(pricing_profile_router)
router.include_router(pricing_supplier_settings_router)
router.include_router(pricing_supplier_type_mapping_router)
router.include_router(pricing_category_settings_router)
router.include_router(pricing_recompute_router)
# Other admin namespaces
router.include_router(supplier_admin_router)
router.include_router(logistics_admin_router)
router.include_router(logistics_admin_shipments_router)
router.include_router(admin_order_router)
router.include_router(geo_admin_router)
router.include_router(activity_admin_router)

# === Webhooks ===
router.include_router(dobropost_webhook_router)
router.include_router(webhook_router)
router.include_router(payment_webhook_router)
