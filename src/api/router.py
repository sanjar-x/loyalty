# src/api/router.py
from fastapi import APIRouter

from src.modules.catalog.presentation.router import category_router

router = APIRouter()
router.include_router(category_router, prefix="/catalog")
