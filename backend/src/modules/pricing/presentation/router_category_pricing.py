"""FastAPI router for category-pricing-settings endpoints.

FRD §Category Pricing Settings API.
"""

from __future__ import annotations

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_current_identity_id,
)
from src.modules.pricing.application.commands.delete_category_pricing_settings import (
    DeleteCategoryPricingSettingsCommand,
    DeleteCategoryPricingSettingsHandler,
)
from src.modules.pricing.application.commands.upsert_category_pricing_settings import (
    UpsertCategoryPricingSettingsCommand,
    UpsertCategoryPricingSettingsHandler,
)
from src.modules.pricing.application.queries.category_pricing_settings import (
    GetCategoryPricingSettingsHandler,
    GetCategoryPricingSettingsQuery,
)
from src.modules.pricing.domain.entities.category_pricing_settings import (
    CategoryPricingSettings,
    RangeBucket,
)
from src.modules.pricing.presentation.schemas import (
    CategoryPricingSettingsResponse,
    RangeBucketSchema,
    UpsertCategoryPricingSettingsRequest,
    UpsertCategoryPricingSettingsResponse,
)

pricing_category_settings_router = APIRouter(
    prefix="/pricing/categories/{category_id}/pricing",
    tags=["Pricing Category Settings"],
    route_class=DishkaRoute,
)


def _range_to_schema(bucket: RangeBucket) -> RangeBucketSchema:
    return RangeBucketSchema(
        id=bucket.id, min=bucket.min, max=bucket.max, values=dict(bucket.values)
    )


def _range_from_schema(schema: RangeBucketSchema) -> RangeBucket:
    return RangeBucket(
        id=schema.id, min=schema.min, max=schema.max, values=dict(schema.values)
    )


def _to_response(settings: CategoryPricingSettings) -> CategoryPricingSettingsResponse:
    return CategoryPricingSettingsResponse(
        id=settings.id,
        category_id=settings.category_id,
        context_id=settings.context_id,
        values=dict(settings.values),
        ranges=[_range_to_schema(r) for r in settings.ranges],
        explicit_no_ranges=settings.explicit_no_ranges,
        version_lock=settings.version_lock,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
        updated_by=settings.updated_by,
    )


@pricing_category_settings_router.get(
    "",
    response_model=CategoryPricingSettingsResponse,
    summary="Get per-(category, context) pricing settings (direct — no inheritance)",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def get_category_pricing_settings(
    category_id: uuid.UUID,
    handler: FromDishka[GetCategoryPricingSettingsHandler],
    context_id: uuid.UUID = Query(..., description="Target pricing context id"),
) -> CategoryPricingSettingsResponse:
    settings = await handler.handle(
        GetCategoryPricingSettingsQuery(category_id=category_id, context_id=context_id)
    )
    return _to_response(settings)


@pricing_category_settings_router.put(
    "/{context_id}",
    response_model=UpsertCategoryPricingSettingsResponse,
    summary="Create or fully replace pricing settings for (category, context)",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def upsert_category_pricing_settings(
    category_id: uuid.UUID,
    context_id: uuid.UUID,
    body: UpsertCategoryPricingSettingsRequest,
    handler: FromDishka[UpsertCategoryPricingSettingsHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> UpsertCategoryPricingSettingsResponse:
    result = await handler.handle(
        UpsertCategoryPricingSettingsCommand(
            category_id=category_id,
            context_id=context_id,
            values=dict(body.values),
            ranges=[_range_from_schema(r) for r in body.ranges],
            explicit_no_ranges=body.explicit_no_ranges,
            actor_id=identity_id,
            expected_version_lock=body.expected_version_lock,
        )
    )
    return UpsertCategoryPricingSettingsResponse(
        settings_id=result.settings_id,
        category_id=result.category_id,
        context_id=result.context_id,
        version_lock=result.version_lock,
        created=result.created,
    )


@pricing_category_settings_router.delete(
    "/{context_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete pricing settings for (category, context)",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def delete_category_pricing_settings(
    category_id: uuid.UUID,
    context_id: uuid.UUID,
    handler: FromDishka[DeleteCategoryPricingSettingsHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> None:
    await handler.handle(
        DeleteCategoryPricingSettingsCommand(
            category_id=category_id,
            context_id=context_id,
            actor_id=identity_id,
        )
    )
