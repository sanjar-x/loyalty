"""
FastAPI router for Category-Attribute Binding endpoints.

Nested under ``/catalog/categories/{category_id}/attributes``.
All mutating endpoints require the ``catalog:manage`` permission.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.catalog.application.commands.bind_attribute_to_category import (
    BindAttributeToCategoryCommand,
    BindAttributeToCategoryHandler,
    BindAttributeToCategoryResult,
)
from src.modules.catalog.application.commands.bulk_update_requirement_levels import (
    BulkUpdateRequirementLevelsCommand,
    BulkUpdateRequirementLevelsHandler,
    RequirementLevelUpdateItem,
)
from src.modules.catalog.application.commands.reorder_category_bindings import (
    BindingReorderItem,
    ReorderCategoryBindingsCommand,
    ReorderCategoryBindingsHandler,
)
from src.modules.catalog.application.commands.unbind_attribute_from_category import (
    UnbindAttributeFromCategoryCommand,
    UnbindAttributeFromCategoryHandler,
)
from src.modules.catalog.application.commands.update_category_attribute_binding import (
    UpdateCategoryAttributeBindingCommand,
    UpdateCategoryAttributeBindingHandler,
    UpdateCategoryAttributeBindingResult,
)
from src.modules.catalog.application.queries.list_category_bindings import (
    ListCategoryBindingsHandler,
    ListCategoryBindingsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    CategoryAttributeBindingListReadModel,
)
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.modules.catalog.presentation.schemas import (
    BindAttributeToCategoryRequest,
    BindAttributeToCategoryResponse,
    BulkUpdateRequirementLevelsRequest,
    CategoryAttributeBindingListResponse,
    CategoryAttributeBindingResponse,
    ReorderBindingsRequest,
    UpdateBindingRequest,
)
from src.modules.identity.presentation.dependencies import RequirePermission

category_binding_router = APIRouter(
    prefix="/categories/{category_id}/attributes",
    tags=["Category-Attribute Bindings"],
    route_class=DishkaRoute,
)


@category_binding_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=BindAttributeToCategoryResponse,
    summary="Bind an attribute to a category",
    description="Create a binding between an attribute and a category.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def bind_attribute_to_category(
    category_id: uuid.UUID,
    request: BindAttributeToCategoryRequest,
    handler: FromDishka[BindAttributeToCategoryHandler],
) -> BindAttributeToCategoryResponse:
    command = BindAttributeToCategoryCommand(
        category_id=category_id,
        attribute_id=request.attribute_id,
        sort_order=request.sort_order,
        requirement_level=RequirementLevel(request.requirement_level),
        flag_overrides=request.flag_overrides,
        filter_settings=request.filter_settings,
    )
    result: BindAttributeToCategoryResult = await handler.handle(command)
    return BindAttributeToCategoryResponse(binding_id=result.binding_id)


@category_binding_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=CategoryAttributeBindingListResponse,
    summary="List attribute bindings for a category",
    description="Retrieve a paginated list of attribute bindings for a category.",
)
async def list_category_bindings(
    category_id: uuid.UUID,
    handler: FromDishka[ListCategoryBindingsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> CategoryAttributeBindingListResponse:
    query = ListCategoryBindingsQuery(
        category_id=category_id, offset=offset, limit=limit
    )
    result: CategoryAttributeBindingListReadModel = await handler.handle(query)
    return CategoryAttributeBindingListResponse(
        items=[
            CategoryAttributeBindingResponse(
                id=item.id,
                category_id=item.category_id,
                attribute_id=item.attribute_id,
                sort_order=item.sort_order,
                requirement_level=item.requirement_level,
                flag_overrides=item.flag_overrides,
                filter_settings=item.filter_settings,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@category_binding_router.patch(
    path="/{binding_id}",
    status_code=status.HTTP_200_OK,
    response_model=CategoryAttributeBindingResponse,
    summary="Update a category-attribute binding",
    description="Partially update binding fields like sort order or requirement level.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_binding(
    category_id: uuid.UUID,
    binding_id: uuid.UUID,
    request: UpdateBindingRequest,
    handler: FromDishka[UpdateCategoryAttributeBindingHandler],
) -> CategoryAttributeBindingResponse:
    command = UpdateCategoryAttributeBindingCommand(
        binding_id=binding_id,
        sort_order=request.sort_order,
        requirement_level=(
            RequirementLevel(request.requirement_level)
            if request.requirement_level
            else None
        ),
        flag_overrides=request.flag_overrides,
        filter_settings=request.filter_settings,
    )
    result: UpdateCategoryAttributeBindingResult = await handler.handle(command)

    return CategoryAttributeBindingResponse(
        id=result.id,
        category_id=result.category_id,
        attribute_id=result.attribute_id,
        sort_order=result.sort_order,
        requirement_level=result.requirement_level,
        flag_overrides=result.flag_overrides,
        filter_settings=result.filter_settings,
    )


@category_binding_router.delete(
    path="/{binding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unbind an attribute from a category",
    description="Remove the binding between an attribute and a category.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def unbind_attribute(
    category_id: uuid.UUID,
    binding_id: uuid.UUID,
    handler: FromDishka[UnbindAttributeFromCategoryHandler],
) -> None:
    command = UnbindAttributeFromCategoryCommand(binding_id=binding_id)
    await handler.handle(command)


@category_binding_router.post(
    path="/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bulk reorder bindings within a category",
    description="Set new sort orders for multiple bindings at once.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def reorder_bindings(
    category_id: uuid.UUID,
    request: ReorderBindingsRequest,
    handler: FromDishka[ReorderCategoryBindingsHandler],
) -> None:
    command = ReorderCategoryBindingsCommand(
        category_id=category_id,
        items=[
            BindingReorderItem(binding_id=item.binding_id, sort_order=item.sort_order)
            for item in request.items
        ],
    )
    await handler.handle(command)


@category_binding_router.post(
    path="/bulk-requirement-level",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bulk update requirement levels for bindings",
    description="Update requirement levels for multiple bindings at once.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def bulk_update_requirement_levels(
    category_id: uuid.UUID,
    request: BulkUpdateRequirementLevelsRequest,
    handler: FromDishka[BulkUpdateRequirementLevelsHandler],
) -> None:
    command = BulkUpdateRequirementLevelsCommand(
        category_id=category_id,
        items=[
            RequirementLevelUpdateItem(
                binding_id=item.binding_id,
                requirement_level=RequirementLevel(item.requirement_level),
            )
            for item in request.items
        ],
    )
    await handler.handle(command)
