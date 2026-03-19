"""
FastAPI router for AttributeGroup CRUD endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.catalog.application.commands.create_attribute_group import (
    CreateAttributeGroupCommand,
    CreateAttributeGroupHandler,
    CreateAttributeGroupResult,
)
from src.modules.catalog.application.commands.delete_attribute_group import (
    DeleteAttributeGroupCommand,
    DeleteAttributeGroupHandler,
)
from src.modules.catalog.application.commands.update_attribute_group import (
    UpdateAttributeGroupCommand,
    UpdateAttributeGroupHandler,
    UpdateAttributeGroupResult,
)
from src.modules.catalog.application.queries.get_attribute_group import (
    GetAttributeGroupHandler,
)
from src.modules.catalog.application.queries.list_attribute_groups import (
    ListAttributeGroupsHandler,
    ListAttributeGroupsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    AttributeGroupListReadModel,
    AttributeGroupReadModel,
)
from src.modules.catalog.presentation.schemas import (
    AttributeGroupCreateRequest,
    AttributeGroupCreateResponse,
    AttributeGroupListResponse,
    AttributeGroupResponse,
    AttributeGroupUpdateRequest,
)
from src.modules.identity.presentation.dependencies import RequirePermission

attribute_group_router = APIRouter(
    prefix="/attribute-groups",
    tags=["Attribute Groups"],
    route_class=DishkaRoute,
)


@attribute_group_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=AttributeGroupCreateResponse,
    summary="Create a new attribute group",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_attribute_group(
    request: AttributeGroupCreateRequest,
    handler: FromDishka[CreateAttributeGroupHandler],
) -> AttributeGroupCreateResponse:
    command = CreateAttributeGroupCommand(
        code=request.code,
        name_i18n=request.name_i18n,
        sort_order=request.sort_order,
    )
    result: CreateAttributeGroupResult = await handler.handle(command)
    return AttributeGroupCreateResponse(group_id=result.group_id)


@attribute_group_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=AttributeGroupListResponse,
    summary="List attribute groups (paginated)",
)
async def list_attribute_groups(
    handler: FromDishka[ListAttributeGroupsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> AttributeGroupListResponse:
    query = ListAttributeGroupsQuery(offset=offset, limit=limit)
    result: AttributeGroupListReadModel = await handler.handle(query)
    return AttributeGroupListResponse(
        items=[
            AttributeGroupResponse(
                id=item.id,
                code=item.code,
                name_i18n=item.name_i18n,
                sort_order=item.sort_order,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@attribute_group_router.get(
    path="/{group_id}",
    status_code=status.HTTP_200_OK,
    response_model=AttributeGroupResponse,
    summary="Get attribute group by ID",
)
async def get_attribute_group(
    group_id: uuid.UUID,
    handler: FromDishka[GetAttributeGroupHandler],
) -> AttributeGroupResponse:
    result: AttributeGroupReadModel = await handler.handle(group_id)
    return AttributeGroupResponse(
        id=result.id,
        code=result.code,
        name_i18n=result.name_i18n,
        sort_order=result.sort_order,
    )


@attribute_group_router.patch(
    path="/{group_id}",
    status_code=status.HTTP_200_OK,
    response_model=AttributeGroupResponse,
    summary="Update an attribute group",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_attribute_group(
    group_id: uuid.UUID,
    request: AttributeGroupUpdateRequest,
    handler: FromDishka[UpdateAttributeGroupHandler],
) -> AttributeGroupResponse:
    command = UpdateAttributeGroupCommand(
        group_id=group_id,
        name_i18n=request.name_i18n,
        sort_order=request.sort_order,
    )
    result: UpdateAttributeGroupResult = await handler.handle(command)
    return AttributeGroupResponse(
        id=result.id,
        code=result.code,
        name_i18n=result.name_i18n,
        sort_order=result.sort_order,
    )


@attribute_group_router.delete(
    path="/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attribute group",
    description="Deletes the group and moves its attributes to the 'general' group.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_attribute_group(
    group_id: uuid.UUID,
    handler: FromDishka[DeleteAttributeGroupHandler],
) -> None:
    command = DeleteAttributeGroupCommand(group_id=group_id, move_to_general=True)
    await handler.handle(command)
