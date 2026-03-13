# src/api/router.py
from fastapi import APIRouter

from src.modules.catalog.presentation.router import brand_router, category_router

router = APIRouter()
router.include_router(category_router, prefix="/catalog")
router.include_router(brand_router, prefix="/catalog")
