"""
FastAPI router for AttributeGroup CRUD endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Read endpoints require the ``catalog:read`` permission (admin use).
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, Response, status

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
from src.modules.catalog.presentation.update_helpers import build_update_command
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
    description="Create a new attribute group with a unique code and multilingual name.",
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
    return AttributeGroupCreateResponse(id=result.group_id)


@attribute_group_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=AttributeGroupListResponse,
    summary="List attribute groups (paginated)",
    description="Retrieve a paginated list of all attribute groups ordered by sort_order.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_attribute_groups(
    response: Response,
    handler: FromDishka[ListAttributeGroupsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> AttributeGroupListResponse:
    response.headers["Cache-Control"] = "no-store"
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
    description="Retrieve a single attribute group by its unique identifier.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_attribute_group(
    group_id: uuid.UUID,
    response: Response,
    handler: FromDishka[GetAttributeGroupHandler],
) -> AttributeGroupResponse:
    response.headers["Cache-Control"] = "no-store"
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
    description="Partially update attribute group fields. Code is immutable.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_attribute_group(
    group_id: uuid.UUID,
    request: AttributeGroupUpdateRequest,
    handler: FromDishka[UpdateAttributeGroupHandler],
) -> AttributeGroupResponse:
    command = build_update_command(
        request,
        UpdateAttributeGroupCommand,
        group_id=group_id,
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
    description="Permanently delete an attribute group. The 'general' group cannot be deleted.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_attribute_group(
    group_id: uuid.UUID,
    handler: FromDishka[DeleteAttributeGroupHandler],
) -> None:
    command = DeleteAttributeGroupCommand(group_id=group_id)
    await handler.handle(command)
