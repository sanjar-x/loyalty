"""
FastAPI router for AttributeValue CRUD and reorder endpoints.

Nested under ``/catalog/attributes/{attribute_id}/values``.
All mutating endpoints require the ``catalog:manage`` permission.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.catalog.application.commands.add_attribute_value import (
    AddAttributeValueCommand,
    AddAttributeValueHandler,
    AddAttributeValueResult,
)
from src.modules.catalog.application.commands.delete_attribute_value import (
    DeleteAttributeValueCommand,
    DeleteAttributeValueHandler,
)
from src.modules.catalog.application.commands.reorder_attribute_values import (
    ReorderAttributeValuesCommand,
    ReorderAttributeValuesHandler,
    ReorderItem,
)
from src.modules.catalog.application.commands.update_attribute_value import (
    UpdateAttributeValueCommand,
    UpdateAttributeValueHandler,
    UpdateAttributeValueResult,
)
from src.modules.catalog.application.queries.list_attribute_values import (
    ListAttributeValuesHandler,
    ListAttributeValuesQuery,
)
from src.modules.catalog.application.queries.read_models import (
    AttributeValueListReadModel,
)
from src.modules.catalog.presentation.schemas import (
    AttributeValueCreateRequest,
    AttributeValueCreateResponse,
    AttributeValueListResponse,
    AttributeValueResponse,
    AttributeValueUpdateRequest,
    ReorderAttributeValuesRequest,
)
from src.modules.identity.presentation.dependencies import RequirePermission

attribute_value_router = APIRouter(
    prefix="/attributes/{attribute_id}/values",
    tags=["Attribute Values"],
    route_class=DishkaRoute,
)


@attribute_value_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=AttributeValueCreateResponse,
    summary="Add a value to an attribute",
    description="Add a new dictionary value to the specified attribute.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def add_attribute_value(
    attribute_id: uuid.UUID,
    request: AttributeValueCreateRequest,
    handler: FromDishka[AddAttributeValueHandler],
) -> AttributeValueCreateResponse:
    command = AddAttributeValueCommand(
        attribute_id=attribute_id,
        code=request.code,
        slug=request.slug,
        value_i18n=request.value_i18n,
        search_aliases=request.search_aliases,
        meta_data=request.meta_data,
        value_group=request.value_group,
        sort_order=request.sort_order,
    )
    result: AddAttributeValueResult = await handler.handle(command)
    return AttributeValueCreateResponse(value_id=result.value_id)


@attribute_value_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=AttributeValueListResponse,
    summary="List values for an attribute (paginated)",
    description="Retrieve a paginated list of values for an attribute.",
)
async def list_attribute_values(
    attribute_id: uuid.UUID,
    handler: FromDishka[ListAttributeValuesHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None, min_length=1, max_length=100),
) -> AttributeValueListResponse:
    query = ListAttributeValuesQuery(
        attribute_id=attribute_id,
        offset=offset,
        limit=limit,
        search=search,
    )
    result: AttributeValueListReadModel = await handler.handle(query)
    return AttributeValueListResponse(
        items=[
            AttributeValueResponse(
                id=item.id,
                attribute_id=item.attribute_id,
                code=item.code,
                slug=item.slug,
                value_i18n=item.value_i18n,
                search_aliases=item.search_aliases,
                meta_data=item.meta_data,
                value_group=item.value_group,
                sort_order=item.sort_order,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@attribute_value_router.patch(
    path="/{value_id}",
    status_code=status.HTTP_200_OK,
    response_model=AttributeValueResponse,
    summary="Update an attribute value",
    description="Partially update an attribute value. Only provided fields change.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_attribute_value(
    attribute_id: uuid.UUID,
    value_id: uuid.UUID,
    request: AttributeValueUpdateRequest,
    handler: FromDishka[UpdateAttributeValueHandler],
) -> AttributeValueResponse:
    command = UpdateAttributeValueCommand(
        attribute_id=attribute_id,
        value_id=value_id,
        value_i18n=request.value_i18n,
        search_aliases=request.search_aliases,
        meta_data=request.meta_data,
        value_group=request.value_group,
        sort_order=request.sort_order,
    )
    result: UpdateAttributeValueResult = await handler.handle(command)

    return AttributeValueResponse(
        id=result.id,
        attribute_id=result.attribute_id,
        code=result.code,
        slug=result.slug,
        value_i18n=result.value_i18n,
        search_aliases=result.search_aliases,
        meta_data=result.meta_data,
        value_group=result.value_group,
        sort_order=result.sort_order,
    )


@attribute_value_router.delete(
    path="/{value_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attribute value",
    description="Permanently delete a value from the attribute.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_attribute_value(
    attribute_id: uuid.UUID,
    value_id: uuid.UUID,
    handler: FromDishka[DeleteAttributeValueHandler],
) -> None:
    command = DeleteAttributeValueCommand(
        attribute_id=attribute_id,
        value_id=value_id,
    )
    await handler.handle(command)


@attribute_value_router.post(
    path="/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bulk reorder attribute values",
    description="Set new sort orders for multiple attribute values at once.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def reorder_attribute_values(
    attribute_id: uuid.UUID,
    request: ReorderAttributeValuesRequest,
    handler: FromDishka[ReorderAttributeValuesHandler],
) -> None:
    command = ReorderAttributeValuesCommand(
        attribute_id=attribute_id,
        items=[
            ReorderItem(value_id=item.value_id, sort_order=item.sort_order)
            for item in request.items
        ],
    )
    await handler.handle(command)
