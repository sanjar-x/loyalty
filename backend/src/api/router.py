"""Root API router that aggregates all module-level routers.

This module acts as the single entry point for all versioned API routes.
Each bounded-context module registers its own sub-router here, grouped
under an appropriate URL prefix.
"""

from fastapi import APIRouter

from src.modules.catalog.presentation.router_attribute_groups import (
    attribute_group_router,
)
from src.modules.catalog.presentation.router_attribute_values import (
    attribute_value_router,
)
from src.modules.catalog.presentation.router_attributes import attribute_router
from src.modules.catalog.presentation.router_brands import brand_router
from src.modules.catalog.presentation.router_categories import category_router
from src.modules.catalog.presentation.router_category_bindings import (
    category_binding_router,
)
from src.modules.catalog.presentation.router_product_attributes import (
    product_attribute_router,
)
from src.modules.catalog.presentation.router_products import product_router
from src.modules.catalog.presentation.router_skus import sku_router
from src.modules.catalog.presentation.router_storefront import storefront_router
from src.modules.geo.presentation.router import geo_router
from src.modules.identity.presentation.router_account import identity_account_router
from src.modules.identity.presentation.router_admin import admin_router
from src.modules.identity.presentation.router_auth import auth_router
from src.modules.identity.presentation.router_customers import customer_admin_router
from src.modules.identity.presentation.router_invitation import invitation_router
from src.modules.identity.presentation.router_staff import staff_admin_router
from src.modules.user.presentation.router import user_router

router = APIRouter()
router.include_router(category_router, prefix="/catalog")
router.include_router(brand_router, prefix="/catalog")
router.include_router(attribute_group_router, prefix="/catalog")
router.include_router(attribute_router, prefix="/catalog")
router.include_router(attribute_value_router, prefix="/catalog")
router.include_router(category_binding_router, prefix="/catalog")
router.include_router(storefront_router, prefix="/catalog")
router.include_router(product_router, prefix="/catalog")
router.include_router(sku_router, prefix="/catalog")
router.include_router(product_attribute_router, prefix="/catalog")
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(staff_admin_router)
router.include_router(customer_admin_router)
router.include_router(invitation_router)
router.include_router(user_router)
router.include_router(identity_account_router)
router.include_router(geo_router)
