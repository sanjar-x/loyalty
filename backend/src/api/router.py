"""Root API router that aggregates all module-level routers.

This module acts as the single entry point for all versioned API routes.
Each bounded-context module registers its own sub-router here, grouped
under an appropriate URL prefix.
"""

from fastapi import APIRouter

from src.modules.activity.presentation.router_admin import activity_admin_router
from src.modules.cart.presentation.router_customer import cart_router
from src.modules.catalog.presentation.router_attribute_groups import (
    attribute_group_router,
)
from src.modules.catalog.presentation.router_attribute_templates import (
    attribute_template_router,
)
from src.modules.catalog.presentation.router_attribute_values import (
    attribute_value_router,
)
from src.modules.catalog.presentation.router_attributes import attribute_router
from src.modules.catalog.presentation.router_brands import brand_router
from src.modules.catalog.presentation.router_categories import category_router
from src.modules.catalog.presentation.router_media import media_router
from src.modules.catalog.presentation.router_product_attributes import (
    product_attribute_router,
)
from src.modules.catalog.presentation.router_products import product_router
from src.modules.catalog.presentation.router_skus import sku_router
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
from src.modules.catalog.presentation.router_storefront_trending import (
    storefront_trending_router,
)
from src.modules.catalog.presentation.router_variants import variant_router
from src.modules.geo.presentation.router_admin import geo_admin_router
from src.modules.geo.presentation.router_geo import geo_router
from src.modules.identity.presentation.router_account import identity_account_router
from src.modules.identity.presentation.router_admin import admin_router
from src.modules.identity.presentation.router_auth import auth_router
from src.modules.identity.presentation.router_customers import customer_admin_router
from src.modules.identity.presentation.router_invitation import invitation_router
from src.modules.identity.presentation.router_staff import staff_admin_router
from src.modules.logistics.presentation.router_logistics import logistics_router
from src.modules.logistics.presentation.router_webhooks import webhook_router
from src.modules.pricing.presentation.router_category_pricing import (
    pricing_category_settings_router,
)
from src.modules.pricing.presentation.router_context import pricing_context_router
from src.modules.pricing.presentation.router_formula import pricing_formula_router
from src.modules.pricing.presentation.router_preview import pricing_preview_router
from src.modules.pricing.presentation.router_product_pricing import (
    pricing_profile_router,
)
from src.modules.pricing.presentation.router_supplier_pricing import (
    pricing_supplier_settings_router,
)
from src.modules.pricing.presentation.router_supplier_type_mapping import (
    pricing_supplier_type_mapping_router,
)
from src.modules.pricing.presentation.router_variable import pricing_variable_router
from src.modules.supplier.presentation.router_suppliers import supplier_router
from src.modules.user.presentation.router_profile import profile_router

router = APIRouter()
router.include_router(category_router, prefix="/catalog")
router.include_router(brand_router, prefix="/catalog")
router.include_router(attribute_router, prefix="/catalog")
router.include_router(attribute_group_router, prefix="/catalog")
router.include_router(attribute_value_router, prefix="/catalog")
router.include_router(attribute_template_router, prefix="/catalog")
router.include_router(storefront_router, prefix="/catalog")
router.include_router(storefront_products_router, prefix="/catalog")
router.include_router(storefront_search_router, prefix="/catalog")
router.include_router(storefront_trending_router, prefix="/catalog")
router.include_router(storefront_for_you_router, prefix="/catalog")
router.include_router(activity_admin_router)
router.include_router(product_router, prefix="/catalog")
router.include_router(variant_router, prefix="/catalog")
router.include_router(sku_router, prefix="/catalog")
router.include_router(product_attribute_router, prefix="/catalog")
router.include_router(media_router, prefix="/catalog")
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(staff_admin_router)
router.include_router(customer_admin_router)
router.include_router(invitation_router)
router.include_router(profile_router)
router.include_router(identity_account_router)
router.include_router(geo_router)
router.include_router(geo_admin_router)
router.include_router(supplier_router)
router.include_router(cart_router)
router.include_router(logistics_router)
router.include_router(webhook_router)
router.include_router(pricing_profile_router)
router.include_router(pricing_variable_router)
router.include_router(pricing_context_router)
router.include_router(pricing_formula_router)
router.include_router(pricing_category_settings_router)
router.include_router(pricing_supplier_type_mapping_router)
router.include_router(pricing_supplier_settings_router)
router.include_router(pricing_preview_router)
