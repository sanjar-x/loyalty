"""
FastAPI router for Attribute CRUD endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.catalog.application.commands.create_attribute import (
    CreateAttributeCommand,
    CreateAttributeHandler,
    CreateAttributeResult,
)
from src.modules.catalog.application.commands.delete_attribute import (
    DeleteAttributeCommand,
    DeleteAttributeHandler,
)
from src.modules.catalog.application.commands.update_attribute import (
    UpdateAttributeCommand,
    UpdateAttributeHandler,
    UpdateAttributeResult,
)
from src.modules.catalog.application.queries.get_attribute import GetAttributeHandler
from src.modules.catalog.application.queries.list_attributes import (
    ListAttributesHandler,
    ListAttributesQuery,
)
from src.modules.catalog.application.queries.read_models import (
    AttributeListReadModel,
    AttributeReadModel,
)
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
)
from src.modules.catalog.presentation.schemas import (
    AttributeCreateRequest,
    AttributeCreateResponse,
    AttributeListResponse,
    AttributeResponse,
    AttributeUpdateRequest,
)
from src.modules.identity.presentation.dependencies import RequirePermission

attribute_router = APIRouter(
    prefix="/attributes",
    tags=["Attributes"],
    route_class=DishkaRoute,
)


@attribute_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=AttributeCreateResponse,
    summary="Create a new attribute",
    description="Create a new attribute with full configuration options.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_attribute(
    request: AttributeCreateRequest,
    handler: FromDishka[CreateAttributeHandler],
) -> AttributeCreateResponse:
    command = CreateAttributeCommand(
        code=request.code,
        slug=request.slug,
        name_i18n=request.name_i18n,
        description_i18n=request.description_i18n,
        data_type=AttributeDataType(request.data_type),
        ui_type=AttributeUIType(request.ui_type),
        is_dictionary=request.is_dictionary,
        group_id=request.group_id,
        level=AttributeLevel(request.level),
        is_filterable=request.is_filterable,
        is_searchable=request.is_searchable,
        search_weight=request.search_weight,
        is_comparable=request.is_comparable,
        is_visible_on_card=request.is_visible_on_card,
        is_visible_in_catalog=request.is_visible_in_catalog,
        validation_rules=request.validation_rules,
    )
    result: CreateAttributeResult = await handler.handle(command)
    return AttributeCreateResponse(attribute_id=result.attribute_id)


@attribute_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=AttributeListResponse,
    summary="List attributes (paginated, filterable)",
    description="Retrieve a paginated list of attributes with optional filters.",
)
async def list_attributes(
    handler: FromDishka[ListAttributesHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    data_type: str | None = Query(default=None),
    ui_type: str | None = Query(default=None),
    is_dictionary: bool | None = Query(default=None),
    group_id: uuid.UUID | None = Query(default=None),
    level: str | None = Query(default=None),
    is_filterable: bool | None = Query(default=None),
    is_searchable: bool | None = Query(default=None),
    is_comparable: bool | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=100),
) -> AttributeListResponse:
    query = ListAttributesQuery(
        offset=offset,
        limit=limit,
        data_type=data_type,
        ui_type=ui_type,
        is_dictionary=is_dictionary,
        group_id=group_id,
        level=level,
        is_filterable=is_filterable,
        is_searchable=is_searchable,
        is_comparable=is_comparable,
        search=search,
    )
    result: AttributeListReadModel = await handler.handle(query)
    return AttributeListResponse(
        items=[
            AttributeResponse(
                id=item.id,
                code=item.code,
                slug=item.slug,
                name_i18n=item.name_i18n,
                description_i18n=item.description_i18n,
                data_type=item.data_type,
                ui_type=item.ui_type,
                is_dictionary=item.is_dictionary,
                group_id=item.group_id,
                level=item.level,
                is_filterable=item.is_filterable,
                is_searchable=item.is_searchable,
                search_weight=item.search_weight,
                is_comparable=item.is_comparable,
                is_visible_on_card=item.is_visible_on_card,
                is_visible_in_catalog=item.is_visible_in_catalog,
                validation_rules=item.validation_rules,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@attribute_router.get(
    path="/by-slug/{slug}",
    status_code=status.HTTP_200_OK,
    response_model=AttributeResponse,
    summary="Get attribute by slug",
    description="Retrieve a single attribute by its URL-friendly slug.",
)
async def get_attribute_by_slug(
    slug: str,
    handler: FromDishka[GetAttributeHandler],
) -> AttributeResponse:
    result: AttributeReadModel = await handler.handle_by_slug(slug)
    return _to_response(result)


@attribute_router.get(
    path="/{attribute_id}",
    status_code=status.HTTP_200_OK,
    response_model=AttributeResponse,
    summary="Get attribute by ID",
    description="Retrieve a single attribute by its unique identifier.",
)
async def get_attribute(
    attribute_id: uuid.UUID,
    handler: FromDishka[GetAttributeHandler],
) -> AttributeResponse:
    result: AttributeReadModel = await handler.handle(attribute_id)
    return _to_response(result)


@attribute_router.patch(
    path="/{attribute_id}",
    status_code=status.HTTP_200_OK,
    response_model=AttributeResponse,
    summary="Update an attribute",
    description="Partially update attribute fields. Only provided fields are modified.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_attribute(
    attribute_id: uuid.UUID,
    request: AttributeUpdateRequest,
    handler: FromDishka[UpdateAttributeHandler],
    get_handler: FromDishka[GetAttributeHandler],
) -> AttributeResponse:
    # Build update command with sentinel handling for validation_rules
    command = UpdateAttributeCommand(
        attribute_id=attribute_id,
        name_i18n=request.name_i18n,
        description_i18n=request.description_i18n,
        ui_type=AttributeUIType(request.ui_type) if request.ui_type else None,
        group_id=request.group_id,
        level=AttributeLevel(request.level) if request.level else None,
        is_filterable=request.is_filterable,
        is_searchable=request.is_searchable,
        search_weight=request.search_weight,
        is_comparable=request.is_comparable,
        is_visible_on_card=request.is_visible_on_card,
        is_visible_in_catalog=request.is_visible_in_catalog,
        validation_rules=request.validation_rules,
    )
    result: UpdateAttributeResult = await handler.handle(command)

    # Fetch the full attribute for response
    read_model: AttributeReadModel = await get_handler.handle(result.id)
    return _to_response(read_model)


@attribute_router.delete(
    path="/{attribute_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attribute",
    description="Permanently delete an attribute by its ID.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_attribute(
    attribute_id: uuid.UUID,
    handler: FromDishka[DeleteAttributeHandler],
) -> None:
    command = DeleteAttributeCommand(attribute_id=attribute_id)
    await handler.handle(command)


def _to_response(model: AttributeReadModel) -> AttributeResponse:
    """Convert a read model to a response schema."""
    return AttributeResponse(
        id=model.id,
        code=model.code,
        slug=model.slug,
        name_i18n=model.name_i18n,
        description_i18n=model.description_i18n,
        data_type=model.data_type,
        ui_type=model.ui_type,
        is_dictionary=model.is_dictionary,
        group_id=model.group_id,
        level=model.level,
        is_filterable=model.is_filterable,
        is_searchable=model.is_searchable,
        search_weight=model.search_weight,
        is_comparable=model.is_comparable,
        is_visible_on_card=model.is_visible_on_card,
        is_visible_in_catalog=model.is_visible_in_catalog,
        validation_rules=model.validation_rules,
    )
