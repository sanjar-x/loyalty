"""FastAPI router for pricing profile management (admin/manager)."""

from __future__ import annotations

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status

from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_current_identity_id,
)
from src.modules.pricing.application.commands.delete_product_pricing_profile import (
    DeleteProductPricingProfileCommand,
    DeleteProductPricingProfileHandler,
)
from src.modules.pricing.application.commands.upsert_product_pricing_profile import (
    UpsertProductPricingProfileCommand,
    UpsertProductPricingProfileHandler,
)
from src.modules.pricing.application.queries.get_product_pricing_profile import (
    GetProductPricingProfileHandler,
    GetProductPricingProfileQuery,
)
from src.modules.pricing.application.queries.required_variables import (
    GetRequiredVariablesHandler,
    GetRequiredVariablesQuery,
)
from src.modules.pricing.presentation.schemas import (
    ProductPricingProfileResponse,
    RequiredVariableItem,
    RequiredVariablesResponse,
    UpsertProductPricingProfileRequest,
    UpsertProductPricingProfileResponse,
)

pricing_profile_router = APIRouter(
    prefix="/pricing/products",
    tags=["Pricing"],
    route_class=DishkaRoute,
)


@pricing_profile_router.get(
    "/{product_id}/profile",
    response_model=ProductPricingProfileResponse,
    summary="Get pricing profile for a product",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def get_profile(
    product_id: uuid.UUID,
    handler: FromDishka[GetProductPricingProfileHandler],
    _identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> ProductPricingProfileResponse:
    read_model = await handler.handle(
        GetProductPricingProfileQuery(product_id=product_id)
    )
    return ProductPricingProfileResponse(
        profile_id=read_model.profile_id,
        product_id=read_model.product_id,
        context_id=read_model.context_id,
        values=read_model.values,
        status=read_model.status,
        version_lock=read_model.version_lock,
        created_at=read_model.created_at,
        updated_at=read_model.updated_at,
        updated_by=read_model.updated_by,
    )


@pricing_profile_router.put(
    "/{product_id}/profile",
    response_model=UpsertProductPricingProfileResponse,
    summary="Create or update the pricing profile for a product",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def upsert_profile(
    product_id: uuid.UUID,
    body: UpsertProductPricingProfileRequest,
    handler: FromDishka[UpsertProductPricingProfileHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> UpsertProductPricingProfileResponse:
    command = UpsertProductPricingProfileCommand(
        product_id=product_id,
        values=dict(body.values),
        actor_id=identity_id,
        context_id=body.context_id,
        context_id_provided=body.context_id_provided,
        status=body.status,
        expected_version_lock=body.expected_version_lock,
    )
    result = await handler.handle(command)
    return UpsertProductPricingProfileResponse(
        profile_id=result.profile_id,
        product_id=result.product_id,
        version_lock=result.version_lock,
        status=result.status,
        created=result.created,
    )


@pricing_profile_router.delete(
    "/{product_id}/profile",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete the pricing profile for a product",
    dependencies=[Depends(RequirePermission(codename="pricing:admin"))],
)
async def delete_profile(
    product_id: uuid.UUID,
    handler: FromDishka[DeleteProductPricingProfileHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> None:
    await handler.handle(
        DeleteProductPricingProfileCommand(
            product_id=product_id,
            actor_id=identity_id,
        )
    )


@pricing_profile_router.get(
    "/{product_id}/profile/required-variables",
    response_model=RequiredVariablesResponse,
    summary="List product_input variables required for this product's pricing profile",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def get_required_variables(
    product_id: uuid.UUID,
    handler: FromDishka[GetRequiredVariablesHandler],
    _identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> RequiredVariablesResponse:
    result = await handler.handle(GetRequiredVariablesQuery(product_id=product_id))
    return RequiredVariablesResponse(
        product_id=result.product_id,
        variables=[
            RequiredVariableItem(
                variable_id=v.variable_id,
                code=v.code,
                name=v.name,
                description=v.description,
                data_type=v.data_type,
                unit=v.unit,
                default_value=v.default_value,
                is_system=v.is_system,
            )
            for v in result.variables
        ],
    )
