"""FastAPI router for supplier-pricing-settings endpoints.

FRD §Supplier Pricing Settings API.
"""

from __future__ import annotations

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends

from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_current_identity_id,
)
from src.modules.pricing.application.commands.upsert_supplier_pricing_settings import (
    UpsertSupplierPricingSettingsCommand,
    UpsertSupplierPricingSettingsHandler,
)
from src.modules.pricing.application.queries.supplier_pricing_settings import (
    GetSupplierPricingSettingsHandler,
    GetSupplierPricingSettingsQuery,
)
from src.modules.pricing.domain.supplier_pricing_settings import (
    SupplierPricingSettings,
)
from src.modules.pricing.presentation.schemas import (
    SupplierPricingSettingsResponse,
    UpsertSupplierPricingSettingsRequest,
    UpsertSupplierPricingSettingsResponse,
)

pricing_supplier_settings_router = APIRouter(
    prefix="/pricing/suppliers/{supplier_id}/pricing",
    tags=["Pricing Supplier Settings"],
    route_class=DishkaRoute,
)


def _to_response(
    settings: SupplierPricingSettings,
) -> SupplierPricingSettingsResponse:
    return SupplierPricingSettingsResponse(
        id=settings.id,
        supplier_id=settings.supplier_id,
        values=dict(settings.values),
        version_lock=settings.version_lock,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
        updated_by=settings.updated_by,
    )


@pricing_supplier_settings_router.get(
    "",
    response_model=SupplierPricingSettingsResponse,
    summary="Get per-supplier pricing settings",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def get_supplier_pricing_settings(
    supplier_id: uuid.UUID,
    handler: FromDishka[GetSupplierPricingSettingsHandler],
) -> SupplierPricingSettingsResponse:
    settings = await handler.handle(
        GetSupplierPricingSettingsQuery(supplier_id=supplier_id)
    )
    return _to_response(settings)


@pricing_supplier_settings_router.put(
    "",
    response_model=UpsertSupplierPricingSettingsResponse,
    summary="Create or fully replace pricing settings for a supplier",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def upsert_supplier_pricing_settings(
    supplier_id: uuid.UUID,
    body: UpsertSupplierPricingSettingsRequest,
    handler: FromDishka[UpsertSupplierPricingSettingsHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> UpsertSupplierPricingSettingsResponse:
    result = await handler.handle(
        UpsertSupplierPricingSettingsCommand(
            supplier_id=supplier_id,
            values=dict(body.values),
            actor_id=identity_id,
            expected_version_lock=body.expected_version_lock,
        )
    )
    return UpsertSupplierPricingSettingsResponse(
        settings_id=result.settings_id,
        supplier_id=result.supplier_id,
        version_lock=result.version_lock,
        created=result.created,
    )
