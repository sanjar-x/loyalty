"""FastAPI router for SupplierType → PricingContext mapping endpoints.

FRD §SupplierType→Context Mapping.
"""

from __future__ import annotations

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status

from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_current_identity_id,
)
from src.modules.pricing.application.commands.delete_supplier_type_context_mapping import (
    DeleteSupplierTypeContextMappingCommand,
    DeleteSupplierTypeContextMappingHandler,
)
from src.modules.pricing.application.commands.upsert_supplier_type_context_mapping import (
    UpsertSupplierTypeContextMappingCommand,
    UpsertSupplierTypeContextMappingHandler,
)
from src.modules.pricing.application.queries.supplier_type_context_mappings import (
    GetSupplierTypeContextMappingHandler,
    GetSupplierTypeContextMappingQuery,
    ListSupplierTypeContextMappingsHandler,
    ListSupplierTypeContextMappingsQuery,
)
from src.modules.pricing.domain.supplier_type_context_mapping import (
    SupplierTypeContextMapping,
)
from src.modules.pricing.presentation.schemas import (
    SupplierTypeContextMappingListResponse,
    SupplierTypeContextMappingResponse,
    UpsertSupplierTypeContextMappingRequest,
    UpsertSupplierTypeContextMappingResponse,
)

pricing_supplier_type_mapping_router = APIRouter(
    prefix="/pricing/supplier-type-mapping",
    tags=["Pricing Supplier-Type Mapping"],
    route_class=DishkaRoute,
)


def _to_response(
    mapping: SupplierTypeContextMapping,
) -> SupplierTypeContextMappingResponse:
    return SupplierTypeContextMappingResponse(
        id=mapping.id,
        supplier_type=mapping.supplier_type,
        context_id=mapping.context_id,
        version_lock=mapping.version_lock,
        created_at=mapping.created_at,
        updated_at=mapping.updated_at,
        updated_by=mapping.updated_by,
    )


@pricing_supplier_type_mapping_router.get(
    "",
    response_model=SupplierTypeContextMappingListResponse,
    summary="List all supplier-type → pricing-context mappings",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def list_supplier_type_context_mappings(
    handler: FromDishka[ListSupplierTypeContextMappingsHandler],
) -> SupplierTypeContextMappingListResponse:
    mappings = await handler.handle(ListSupplierTypeContextMappingsQuery())
    return SupplierTypeContextMappingListResponse(
        items=[_to_response(m) for m in mappings]
    )


@pricing_supplier_type_mapping_router.get(
    "/{supplier_type}",
    response_model=SupplierTypeContextMappingResponse,
    summary="Get a supplier-type → pricing-context mapping",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def get_supplier_type_context_mapping(
    supplier_type: str,
    handler: FromDishka[GetSupplierTypeContextMappingHandler],
) -> SupplierTypeContextMappingResponse:
    mapping = await handler.handle(
        GetSupplierTypeContextMappingQuery(supplier_type=supplier_type)
    )
    return _to_response(mapping)


@pricing_supplier_type_mapping_router.put(
    "/{supplier_type}",
    response_model=UpsertSupplierTypeContextMappingResponse,
    summary="Create or retarget a supplier-type → pricing-context mapping",
    dependencies=[Depends(RequirePermission(codename="pricing:admin"))],
)
async def upsert_supplier_type_context_mapping(
    supplier_type: str,
    body: UpsertSupplierTypeContextMappingRequest,
    handler: FromDishka[UpsertSupplierTypeContextMappingHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> UpsertSupplierTypeContextMappingResponse:
    result = await handler.handle(
        UpsertSupplierTypeContextMappingCommand(
            supplier_type=supplier_type,
            context_id=body.context_id,
            actor_id=identity_id,
        )
    )
    return UpsertSupplierTypeContextMappingResponse(
        mapping_id=result.mapping_id,
        supplier_type=result.supplier_type,
        context_id=result.context_id,
        version_lock=result.version_lock,
        created=result.created,
    )


@pricing_supplier_type_mapping_router.delete(
    "/{supplier_type}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a supplier-type → pricing-context mapping",
    dependencies=[Depends(RequirePermission(codename="pricing:admin"))],
)
async def delete_supplier_type_context_mapping(
    supplier_type: str,
    handler: FromDishka[DeleteSupplierTypeContextMappingHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> None:
    await handler.handle(
        DeleteSupplierTypeContextMappingCommand(
            supplier_type=supplier_type,
            actor_id=identity_id,
        )
    )
