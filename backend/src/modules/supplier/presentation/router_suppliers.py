"""FastAPI router for Supplier CRUD and lifecycle endpoints."""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.identity.presentation.dependencies import RequirePermission
from src.modules.supplier.application.commands.activate_supplier import (
    ActivateSupplierCommand,
    ActivateSupplierHandler,
)
from src.modules.supplier.application.commands.create_supplier import (
    CreateSupplierCommand,
    CreateSupplierHandler,
)
from src.modules.supplier.application.commands.deactivate_supplier import (
    DeactivateSupplierCommand,
    DeactivateSupplierHandler,
)
from src.modules.supplier.application.commands.update_supplier import (
    _UNSET,
    UpdateSupplierCommand,
    UpdateSupplierHandler,
)
from src.modules.supplier.application.queries.get_supplier import GetSupplierHandler
from src.modules.supplier.application.queries.list_suppliers import (
    ListSuppliersHandler,
    ListSuppliersQuery,
)
from src.modules.supplier.domain.value_objects import SupplierType
from src.modules.supplier.presentation.schemas import (
    SupplierCreateRequest,
    SupplierCreateResponse,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdateRequest,
)

supplier_router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
    route_class=DishkaRoute,
)


@supplier_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=SupplierCreateResponse,
    summary="Create a new supplier",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_supplier(
    request: SupplierCreateRequest,
    handler: FromDishka[CreateSupplierHandler],
) -> SupplierCreateResponse:
    command = CreateSupplierCommand(
        name=request.name,
        type=SupplierType(request.type),
        country_code=request.country_code,
        subdivision_code=request.subdivision_code,
    )
    result = await handler.handle(command)
    return SupplierCreateResponse(id=result.supplier_id)


@supplier_router.get(
    path="",
    response_model=SupplierListResponse,
    summary="List all suppliers",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_suppliers(
    handler: FromDishka[ListSuppliersHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> SupplierListResponse:
    query = ListSuppliersQuery(offset=offset, limit=limit)
    result = await handler.handle(query)
    return SupplierListResponse(
        items=[
            SupplierResponse(
                id=s.id,
                name=s.name,
                type=s.type,
                country_code=s.country_code,
                subdivision_code=s.subdivision_code,
                is_active=s.is_active,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@supplier_router.get(
    path="/{supplier_id}",
    response_model=SupplierResponse,
    summary="Get supplier by ID",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_supplier(
    supplier_id: uuid.UUID,
    handler: FromDishka[GetSupplierHandler],
) -> SupplierResponse:
    result = await handler.handle(supplier_id)
    return SupplierResponse(
        id=result.id,
        name=result.name,
        type=result.type,
        country_code=result.country_code,
        subdivision_code=result.subdivision_code,
        is_active=result.is_active,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@supplier_router.put(
    path="/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update supplier",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_supplier(
    supplier_id: uuid.UUID,
    request: SupplierUpdateRequest,
    handler: FromDishka[UpdateSupplierHandler],
) -> None:
    # Use model_fields_set to distinguish "field absent" from "field = null".
    subdivision_code = (
        request.subdivision_code
        if "subdivision_code" in request.model_fields_set
        else _UNSET
    )
    command = UpdateSupplierCommand(
        supplier_id=supplier_id,
        name=request.name,
        country_code=request.country_code,
        subdivision_code=subdivision_code,
    )
    await handler.handle(command)


@supplier_router.patch(
    path="/{supplier_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a supplier",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def deactivate_supplier(
    supplier_id: uuid.UUID,
    handler: FromDishka[DeactivateSupplierHandler],
) -> None:
    await handler.handle(DeactivateSupplierCommand(supplier_id=supplier_id))


@supplier_router.patch(
    path="/{supplier_id}/activate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reactivate a supplier",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def activate_supplier(
    supplier_id: uuid.UUID,
    handler: FromDishka[ActivateSupplierHandler],
) -> None:
    await handler.handle(ActivateSupplierCommand(supplier_id=supplier_id))
