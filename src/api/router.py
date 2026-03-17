"""Root API router that aggregates all module-level routers.

This module acts as the single entry point for all versioned API routes.
Each bounded-context module registers its own sub-router here, grouped
under an appropriate URL prefix.
"""

from fastapi import APIRouter

from src.modules.catalog.presentation.router_brands import brand_router
from src.modules.catalog.presentation.router_categories import category_router
from src.modules.identity.presentation.router_account import identity_account_router
from src.modules.identity.presentation.router_admin import admin_router
from src.modules.identity.presentation.router_auth import auth_router
from src.modules.user.presentation.router import user_router

router = APIRouter()
router.include_router(category_router, prefix="/catalog")
router.include_router(brand_router, prefix="/catalog")
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(user_router)
router.include_router(identity_account_router)
