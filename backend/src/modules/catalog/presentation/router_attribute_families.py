"""
FastAPI router for AttributeFamily CRUD, binding, exclusion, and
effective-attribute endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Read endpoints require the ``catalog:read`` permission (admin use).
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.catalog.application.commands.add_family_exclusion import (
    AddFamilyExclusionCommand,
    AddFamilyExclusionHandler,
    AddFamilyExclusionResult,
)
from src.modules.catalog.application.commands.bind_attribute_to_family import (
    BindAttributeToFamilyCommand,
    BindAttributeToFamilyHandler,
    BindAttributeToFamilyResult,
)
from src.modules.catalog.application.commands.create_attribute_family import (
    CreateAttributeFamilyCommand,
    CreateAttributeFamilyHandler,
    CreateAttributeFamilyResult,
)
from src.modules.catalog.application.commands.delete_attribute_family import (
    DeleteAttributeFamilyCommand,
    DeleteAttributeFamilyHandler,
)
from src.modules.catalog.application.commands.remove_family_exclusion import (
    RemoveFamilyExclusionCommand,
    RemoveFamilyExclusionHandler,
)
from src.modules.catalog.application.commands.reorder_family_bindings import (
    BindingReorderItem,
    ReorderFamilyBindingsCommand,
    ReorderFamilyBindingsHandler,
)
from src.modules.catalog.application.commands.unbind_attribute_from_family import (
    UnbindAttributeFromFamilyCommand,
    UnbindAttributeFromFamilyHandler,
)
from src.modules.catalog.application.commands.update_attribute_family import (
    UpdateAttributeFamilyCommand,
    UpdateAttributeFamilyHandler,
    UpdateAttributeFamilyResult,
)
from src.modules.catalog.application.commands.update_family_attribute_binding import (
    UpdateFamilyAttributeBindingCommand,
    UpdateFamilyAttributeBindingHandler,
)
from src.modules.catalog.application.queries.list_attribute_families import (
    GetAttributeFamilyHandler,
    GetAttributeFamilyQuery,
    GetAttributeFamilyTreeHandler,
    ListAttributeFamiliesHandler,
    ListAttributeFamiliesQuery,
)
from src.modules.catalog.application.queries.list_family_bindings import (
    ListFamilyBindingsHandler,
    ListFamilyBindingsQuery,
)
from src.modules.catalog.application.queries.list_family_exclusions import (
    ListFamilyExclusionsHandler,
    ListFamilyExclusionsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    AttributeFamilyListReadModel,
    AttributeFamilyReadModel,
    AttributeFamilyTreeNode,
)
from src.modules.catalog.application.queries.resolve_family_attributes import (
    EffectiveAttributeSetReadModel,
    ResolveFamilyAttributesHandler,
)
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.modules.catalog.presentation.schemas import (
    AttributeFamilyCreateRequest,
    AttributeFamilyCreateResponse,
    AttributeFamilyListResponse,
    AttributeFamilyResponse,
    AttributeFamilyTreeResponse,
    AttributeFamilyUpdateRequest,
    BindingReorderItemSchema,
    EffectiveAttributeSchema,
    EffectiveAttributeSetResponse,
    EffectiveAttributeValueSchema,
    FamilyAttributeBindingDetailResponse,
    FamilyAttributeBindingListResponse,
    FamilyAttributeBindingRequest,
    FamilyAttributeBindingResponse,
    FamilyAttributeBindingUpdateRequest,
    FamilyAttributeExclusionDetailResponse,
    FamilyAttributeExclusionListResponse,
    FamilyAttributeExclusionRequest,
    FamilyAttributeExclusionResponse,
    FamilyBindingReorderRequest,
)
from src.modules.catalog.presentation.update_helpers import build_update_command
from src.modules.identity.presentation.dependencies import RequirePermission

attribute_family_router = APIRouter(
    prefix="/attribute-families",
    tags=["Attribute Families"],
    route_class=DishkaRoute,
)


# ═══════════════════════════════════════════════════════════════════════════
# Family CRUD
# ═══════════════════════════════════════════════════════════════════════════


@attribute_family_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=AttributeFamilyCreateResponse,
    summary="Create a new attribute family",
    description="Creates a root or child attribute family.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_family(
    request: AttributeFamilyCreateRequest,
    handler: FromDishka[CreateAttributeFamilyHandler],
) -> AttributeFamilyCreateResponse:
    command = CreateAttributeFamilyCommand(
        code=request.code,
        name_i18n=request.name_i18n,
        description_i18n=request.description_i18n,
        parent_id=request.parent_id,
        sort_order=request.sort_order,
    )
    result: CreateAttributeFamilyResult = await handler.handle(command)
    return AttributeFamilyCreateResponse(id=result.id)


@attribute_family_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=AttributeFamilyListResponse,
    summary="List attribute families (paginated)",
    description="Retrieve a paginated list of all attribute families.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_families(
    handler: FromDishka[ListAttributeFamiliesHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> AttributeFamilyListResponse:
    query = ListAttributeFamiliesQuery(offset=offset, limit=limit)
    result: AttributeFamilyListReadModel = await handler.handle(query)
    return AttributeFamilyListResponse(
        items=[
            AttributeFamilyResponse(
                id=item.id,
                parent_id=item.parent_id,
                code=item.code,
                name_i18n=item.name_i18n,
                description_i18n=item.description_i18n,
                sort_order=item.sort_order,
                level=item.level,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@attribute_family_router.get(
    path="/tree",
    status_code=status.HTTP_200_OK,
    response_model=list[AttributeFamilyTreeResponse],
    summary="Get the attribute family tree",
    description="Returns the full attribute family hierarchy as a nested tree.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_family_tree(
    handler: FromDishka[GetAttributeFamilyTreeHandler],
) -> list[AttributeFamilyTreeResponse]:
    roots: list[AttributeFamilyTreeNode] = await handler.handle()
    return [
        AttributeFamilyTreeResponse.model_validate(r, from_attributes=True)
        for r in roots
    ]


@attribute_family_router.get(
    path="/{family_id}",
    status_code=status.HTTP_200_OK,
    response_model=AttributeFamilyResponse,
    summary="Get attribute family by ID",
    description="Retrieve a single attribute family by its unique identifier.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_family(
    family_id: uuid.UUID,
    handler: FromDishka[GetAttributeFamilyHandler],
) -> AttributeFamilyResponse:
    result: AttributeFamilyReadModel = await handler.handle(
        GetAttributeFamilyQuery(family_id=family_id)
    )
    return AttributeFamilyResponse(
        id=result.id,
        parent_id=result.parent_id,
        code=result.code,
        name_i18n=result.name_i18n,
        description_i18n=result.description_i18n,
        sort_order=result.sort_order,
        level=result.level,
    )


@attribute_family_router.patch(
    path="/{family_id}",
    status_code=status.HTTP_200_OK,
    response_model=AttributeFamilyResponse,
    summary="Update an attribute family",
    description="Partially update family fields. Only provided fields are modified.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_family(
    family_id: uuid.UUID,
    request: AttributeFamilyUpdateRequest,
    handler: FromDishka[UpdateAttributeFamilyHandler],
) -> AttributeFamilyResponse:
    command = build_update_command(
        request,
        UpdateAttributeFamilyCommand,
        family_id=family_id,
    )
    result: UpdateAttributeFamilyResult = await handler.handle(command)
    return AttributeFamilyResponse(
        id=result.id,
        parent_id=result.parent_id,
        code=result.code,
        name_i18n=result.name_i18n,
        description_i18n=result.description_i18n,
        sort_order=result.sort_order,
        level=result.level,
    )


@attribute_family_router.delete(
    path="/{family_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attribute family",
    description="Permanently delete a leaf attribute family with no category references.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_family(
    family_id: uuid.UUID,
    handler: FromDishka[DeleteAttributeFamilyHandler],
) -> None:
    command = DeleteAttributeFamilyCommand(family_id=family_id)
    await handler.handle(command)


# ═══════════════════════════════════════════════════════════════════════════
# Family Attribute Bindings
# ═══════════════════════════════════════════════════════════════════════════


@attribute_family_router.post(
    path="/{family_id}/attributes",
    status_code=status.HTTP_201_CREATED,
    response_model=FamilyAttributeBindingResponse,
    summary="Bind an attribute to a family",
    description="Create a new binding between an attribute and a family.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def bind_attribute(
    family_id: uuid.UUID,
    request: FamilyAttributeBindingRequest,
    handler: FromDishka[BindAttributeToFamilyHandler],
) -> FamilyAttributeBindingResponse:
    command = BindAttributeToFamilyCommand(
        family_id=family_id,
        attribute_id=request.attribute_id,
        sort_order=request.sort_order,
        requirement_level=RequirementLevel(request.requirement_level),
        flag_overrides=request.flag_overrides,
        filter_settings=request.filter_settings,
    )
    result: BindAttributeToFamilyResult = await handler.handle(command)
    return FamilyAttributeBindingResponse(id=result.binding_id)


@attribute_family_router.get(
    path="/{family_id}/attributes",
    status_code=status.HTTP_200_OK,
    response_model=FamilyAttributeBindingListResponse,
    summary="List own bindings for a family",
    description="Retrieve a paginated list of attribute bindings directly on this family.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_bindings(
    family_id: uuid.UUID,
    handler: FromDishka[ListFamilyBindingsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> FamilyAttributeBindingListResponse:
    query = ListFamilyBindingsQuery(family_id=family_id, offset=offset, limit=limit)
    result = await handler.handle(query)
    return FamilyAttributeBindingListResponse(
        items=[
            FamilyAttributeBindingDetailResponse(
                id=item.id,
                family_id=item.family_id,
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


@attribute_family_router.get(
    path="/{family_id}/attributes/effective",
    status_code=status.HTTP_200_OK,
    response_model=EffectiveAttributeSetResponse,
    summary="Get effective attributes for a family",
    description="Resolve the full effective attribute set with inheritance.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_effective_attributes(
    family_id: uuid.UUID,
    handler: FromDishka[ResolveFamilyAttributesHandler],
) -> EffectiveAttributeSetResponse:
    result: EffectiveAttributeSetReadModel = await handler.handle(family_id)
    return EffectiveAttributeSetResponse(
        family_id=result.family_id,
        attributes=[
            EffectiveAttributeSchema(
                attribute_id=attr.attribute_id,
                code=attr.code,
                slug=attr.slug,
                name_i18n=attr.name_i18n,
                description_i18n=attr.description_i18n,
                data_type=attr.data_type,
                ui_type=attr.ui_type,
                is_dictionary=attr.is_dictionary,
                level=attr.level,
                requirement_level=attr.requirement_level,
                validation_rules=attr.validation_rules,
                flag_overrides=attr.flag_overrides,
                filter_settings=attr.filter_settings,
                source_family_id=attr.source_family_id,
                is_overridden=attr.is_overridden,
                values=[
                    EffectiveAttributeValueSchema(
                        id=v.id,
                        code=v.code,
                        slug=v.slug,
                        value_i18n=v.value_i18n,
                        meta_data=v.meta_data,
                        value_group=v.value_group,
                        sort_order=v.sort_order,
                    )
                    for v in attr.values
                ],
                sort_order=attr.sort_order,
            )
            for attr in result.attributes
        ],
    )


@attribute_family_router.patch(
    path="/{family_id}/attributes/{binding_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="Update a binding",
    description="Partially update a family-attribute binding.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_binding(
    family_id: uuid.UUID,
    binding_id: uuid.UUID,
    request: FamilyAttributeBindingUpdateRequest,
    handler: FromDishka[UpdateFamilyAttributeBindingHandler],
) -> dict:
    command = build_update_command(
        request,
        UpdateFamilyAttributeBindingCommand,
        field_converters={
            "requirement_level": RequirementLevel,
        },
        binding_id=binding_id,
        family_id=family_id,
    )
    await handler.handle(command)
    return {"message": "Binding updated"}


@attribute_family_router.delete(
    path="/{family_id}/attributes/{binding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unbind an attribute from a family",
    description="Remove a family-attribute binding.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def unbind_attribute(
    family_id: uuid.UUID,
    binding_id: uuid.UUID,
    handler: FromDishka[UnbindAttributeFromFamilyHandler],
) -> None:
    command = UnbindAttributeFromFamilyCommand(
        binding_id=binding_id,
        family_id=family_id,
    )
    await handler.handle(command)


@attribute_family_router.post(
    path="/{family_id}/attributes/reorder",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="Reorder bindings",
    description="Bulk-reorder attribute bindings within a family.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def reorder_bindings(
    family_id: uuid.UUID,
    request: FamilyBindingReorderRequest,
    handler: FromDishka[ReorderFamilyBindingsHandler],
) -> dict:
    command = ReorderFamilyBindingsCommand(
        family_id=family_id,
        items=[
            BindingReorderItem(
                binding_id=item.binding_id,
                sort_order=item.sort_order,
            )
            for item in request.items
        ],
    )
    await handler.handle(command)
    return {"message": "Bindings reordered"}


# ═══════════════════════════════════════════════════════════════════════════
# Family Attribute Exclusions
# ═══════════════════════════════════════════════════════════════════════════


@attribute_family_router.post(
    path="/{family_id}/exclusions",
    status_code=status.HTTP_201_CREATED,
    response_model=FamilyAttributeExclusionResponse,
    summary="Add an attribute exclusion",
    description="Exclude an inherited attribute from a family's effective set.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def add_exclusion(
    family_id: uuid.UUID,
    request: FamilyAttributeExclusionRequest,
    handler: FromDishka[AddFamilyExclusionHandler],
) -> FamilyAttributeExclusionResponse:
    command = AddFamilyExclusionCommand(
        family_id=family_id,
        attribute_id=request.attribute_id,
    )
    result: AddFamilyExclusionResult = await handler.handle(command)
    return FamilyAttributeExclusionResponse(id=result.exclusion_id)


@attribute_family_router.get(
    path="/{family_id}/exclusions",
    status_code=status.HTTP_200_OK,
    response_model=FamilyAttributeExclusionListResponse,
    summary="List exclusions for a family",
    description="Retrieve a paginated list of attribute exclusions for a family.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_exclusions(
    family_id: uuid.UUID,
    handler: FromDishka[ListFamilyExclusionsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> FamilyAttributeExclusionListResponse:
    query = ListFamilyExclusionsQuery(family_id=family_id, offset=offset, limit=limit)
    result = await handler.handle(query)
    return FamilyAttributeExclusionListResponse(
        items=[
            FamilyAttributeExclusionDetailResponse(
                id=item.id,
                family_id=item.family_id,
                attribute_id=item.attribute_id,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@attribute_family_router.delete(
    path="/{family_id}/exclusions/{exclusion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an attribute exclusion",
    description="Remove an attribute exclusion from a family.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def remove_exclusion(
    family_id: uuid.UUID,
    exclusion_id: uuid.UUID,
    handler: FromDishka[RemoveFamilyExclusionHandler],
) -> None:
    command = RemoveFamilyExclusionCommand(
        exclusion_id=exclusion_id,
        family_id=family_id,
    )
    await handler.handle(command)
