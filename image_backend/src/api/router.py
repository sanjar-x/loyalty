"""Root API router that aggregates all module-level routers.

This module acts as the single entry point for all versioned API routes.
"""

from fastapi import APIRouter, Depends

from src.api.dependencies.auth import verify_api_key
from src.modules.storage.presentation.router import media_router

router = APIRouter(dependencies=[Depends(verify_api_key)])
router.include_router(media_router, prefix="/media", tags=["Media"])
