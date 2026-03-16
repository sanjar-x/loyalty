# src/api/router.py
from fastapi import APIRouter

from src.modules.catalog.presentation.router import brand_router, category_router
from src.modules.identity.presentation.router_admin import admin_router
from src.modules.identity.presentation.router_auth import auth_router
from src.modules.user.presentation.router import user_router

router = APIRouter()
router.include_router(category_router, prefix="/catalog")
router.include_router(brand_router, prefix="/catalog")
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(user_router)
