"""
FastAPI router for AttributeTemplate CRUD and binding endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Read endpoints require the ``catalog:read`` permission (admin use).
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, Response, status

from src.modules.catalog.application.commands.bind_attribute_to_template import (
    BindAttributeToTemplateCommand,
    BindAttributeToTemplateHandler,
    BindAttributeToTemplateResult,
)
from src.modules.catalog.application.commands.clone_attribute_template import (
    CloneAttributeTemplateCommand,
    CloneAttributeTemplateHandler,
    CloneAttributeTemplateResult,
)
from src.modules.catalog.application.commands.create_attribute_template import (
    CreateAttributeTemplateCommand,
    CreateAttributeTemplateHandler,
    CreateAttributeTemplateResult,
)
from src.modules.catalog.application.commands.delete_attribute_template import (
    DeleteAttributeTemplateCommand,
    DeleteAttributeTemplateHandler,
)
from src.modules.catalog.application.commands.reorder_template_bindings import (
    BindingReorderItem,
    ReorderTemplateBindingsCommand,
    ReorderTemplateBindingsHandler,
)
from src.modules.catalog.application.commands.unbind_attribute_from_template import (
    UnbindAttributeFromTemplateCommand,
    UnbindAttributeFromTemplateHandler,
)
from src.modules.catalog.application.commands.update_attribute_template import (
    UpdateAttributeTemplateCommand,
    UpdateAttributeTemplateHandler,
    UpdateAttributeTemplateResult,
)
from src.modules.catalog.application.commands.update_template_attribute_binding import (
    UpdateTemplateAttributeBindingCommand,
    UpdateTemplateAttributeBindingHandler,
    UpdateTemplateAttributeBindingResult,
)
from src.modules.catalog.application.queries.list_attribute_templates import (
    GetAttributeTemplateHandler,
    GetAttributeTemplateQuery,
    ListAttributeTemplatesHandler,
    ListAttributeTemplatesQuery,
)
from src.modules.catalog.application.queries.list_template_bindings import (
    ListTemplateBindingsHandler,
    ListTemplateBindingsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    AttributeTemplateListReadModel,
    AttributeTemplateReadModel,
)
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.modules.catalog.presentation.schemas import (
    AttributeTemplateCreateRequest,
    AttributeTemplateCreateResponse,
    AttributeTemplateListResponse,
    AttributeTemplateResponse,
    AttributeTemplateUpdateRequest,
    CloneAttributeTemplateRequest,
    CloneAttributeTemplateResponse,
    TemplateAttributeBindingDetailResponse,
    TemplateAttributeBindingEnrichedResponse,
    TemplateAttributeBindingListResponse,
    TemplateAttributeBindingRequest,
    TemplateAttributeBindingUpdateRequest,
    TemplateBindingReorderRequest,
)
from src.modules.catalog.presentation.update_helpers import build_update_command
from src.modules.identity.presentation.dependencies import RequirePermission

attribute_template_router = APIRouter(
    prefix="/attribute-templates",
    tags=["Attribute Templates"],
    route_class=DishkaRoute,
)


# ═══════════════════════════════════════════════════════════════════════════
# Template CRUD
# ═══════════════════════════════════════════════════════════════════════════


@attribute_template_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=AttributeTemplateCreateResponse,
    summary="Create a new attribute template",
    description="Creates a new attribute template.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_template(
    request: AttributeTemplateCreateRequest,
    handler: FromDishka[CreateAttributeTemplateHandler],
) -> AttributeTemplateCreateResponse:
    command = CreateAttributeTemplateCommand(
        code=request.code,
        name_i18n=request.name_i18n,
        description_i18n=request.description_i18n,
        sort_order=request.sort_order,
    )
    result: CreateAttributeTemplateResult = await handler.handle(command)
    return AttributeTemplateCreateResponse(id=result.id)


@attribute_template_router.post(
    path="/clone",
    status_code=status.HTTP_201_CREATED,
    response_model=CloneAttributeTemplateResponse,
    summary="Clone an attribute template",
    description="Create a copy of an existing template with all its attribute bindings.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def clone_template(
    request: CloneAttributeTemplateRequest,
    handler: FromDishka[CloneAttributeTemplateHandler],
) -> CloneAttributeTemplateResponse:
    command = CloneAttributeTemplateCommand(
        source_template_id=request.source_template_id,
        new_code=request.new_code,
        new_name_i18n=request.new_name_i18n,
        new_description_i18n=request.new_description_i18n,
    )
    result: CloneAttributeTemplateResult = await handler.handle(command)
    return CloneAttributeTemplateResponse(
        id=result.id,
        bindings_copied=result.bindings_copied,
    )


@attribute_template_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=AttributeTemplateListResponse,
    summary="List attribute templates (paginated)",
    description="Retrieve a paginated list of all attribute templates.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_templates(
    response: Response,
    handler: FromDishka[ListAttributeTemplatesHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> AttributeTemplateListResponse:
    response.headers["Cache-Control"] = "no-store"
    query = ListAttributeTemplatesQuery(offset=offset, limit=limit)
    result: AttributeTemplateListReadModel = await handler.handle(query)
    return AttributeTemplateListResponse(
        items=[
            AttributeTemplateResponse(
                id=item.id,
                code=item.code,
                name_i18n=item.name_i18n,
                description_i18n=item.description_i18n,
                sort_order=item.sort_order,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@attribute_template_router.get(
    path="/{template_id}",
    status_code=status.HTTP_200_OK,
    response_model=AttributeTemplateResponse,
    summary="Get attribute template by ID",
    description="Retrieve a single attribute template by its unique identifier.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_template(
    template_id: uuid.UUID,
    response: Response,
    handler: FromDishka[GetAttributeTemplateHandler],
) -> AttributeTemplateResponse:
    response.headers["Cache-Control"] = "no-store"
    result: AttributeTemplateReadModel = await handler.handle(
        GetAttributeTemplateQuery(template_id=template_id)
    )
    return AttributeTemplateResponse(
        id=result.id,
        code=result.code,
        name_i18n=result.name_i18n,
        description_i18n=result.description_i18n,
        sort_order=result.sort_order,
    )


@attribute_template_router.patch(
    path="/{template_id}",
    status_code=status.HTTP_200_OK,
    response_model=AttributeTemplateResponse,
    summary="Update an attribute template",
    description="Partially update template fields. Only provided fields are modified.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_template(
    template_id: uuid.UUID,
    request: AttributeTemplateUpdateRequest,
    handler: FromDishka[UpdateAttributeTemplateHandler],
) -> AttributeTemplateResponse:
    command = build_update_command(
        request,
        UpdateAttributeTemplateCommand,
        template_id=template_id,
    )
    result: UpdateAttributeTemplateResult = await handler.handle(command)
    return AttributeTemplateResponse(
        id=result.id,
        code=result.code,
        name_i18n=result.name_i18n,
        description_i18n=result.description_i18n,
        sort_order=result.sort_order,
    )


@attribute_template_router.delete(
    path="/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attribute template",
    description="Permanently delete an attribute template with no category references.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_template(
    template_id: uuid.UUID,
    handler: FromDishka[DeleteAttributeTemplateHandler],
) -> None:
    command = DeleteAttributeTemplateCommand(template_id=template_id)
    await handler.handle(command)


# ═══════════════════════════════════════════════════════════════════════════
# Template Attribute Bindings
# ═══════════════════════════════════════════════════════════════════════════


@attribute_template_router.post(
    path="/{template_id}/attributes",
    status_code=status.HTTP_201_CREATED,
    response_model=TemplateAttributeBindingEnrichedResponse,
    summary="Bind an attribute to a template",
    description="Create a new binding between an attribute and a template.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def bind_attribute(
    template_id: uuid.UUID,
    request: TemplateAttributeBindingRequest,
    handler: FromDishka[BindAttributeToTemplateHandler],
) -> TemplateAttributeBindingEnrichedResponse:
    command = BindAttributeToTemplateCommand(
        template_id=template_id,
        attribute_id=request.attribute_id,
        sort_order=request.sort_order,
        requirement_level=RequirementLevel(request.requirement_level),
        filter_settings=request.filter_settings,
    )
    result: BindAttributeToTemplateResult = await handler.handle(command)
    return TemplateAttributeBindingEnrichedResponse(
        id=result.binding_id,
        affected_categories_count=result.affected_categories_count,
    )


@attribute_template_router.get(
    path="/{template_id}/attributes",
    status_code=status.HTTP_200_OK,
    response_model=TemplateAttributeBindingListResponse,
    summary="List own bindings for a template",
    description="Retrieve a paginated list of attribute bindings directly on this template.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_bindings(
    template_id: uuid.UUID,
    response: Response,
    handler: FromDishka[ListTemplateBindingsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> TemplateAttributeBindingListResponse:
    response.headers["Cache-Control"] = "no-store"
    query = ListTemplateBindingsQuery(
        template_id=template_id, offset=offset, limit=limit
    )
    result = await handler.handle(query)
    return TemplateAttributeBindingListResponse(
        items=[
            TemplateAttributeBindingDetailResponse(
                id=item.id,
                template_id=item.template_id,
                attribute_id=item.attribute_id,
                sort_order=item.sort_order,
                requirement_level=item.requirement_level,
                filter_settings=item.filter_settings,
                attribute_code=item.attribute_code,
                attribute_name_i18n=item.attribute_name_i18n,
                attribute_data_type=item.attribute_data_type,
                attribute_ui_type=item.attribute_ui_type,
                attribute_level=item.attribute_level,
                attribute_is_filterable=item.attribute_is_filterable,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@attribute_template_router.patch(
    path="/{template_id}/attributes/{binding_id}",
    status_code=status.HTTP_200_OK,
    response_model=TemplateAttributeBindingDetailResponse,
    summary="Update a binding",
    description="Partially update a template-attribute binding.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_binding(
    template_id: uuid.UUID,
    binding_id: uuid.UUID,
    request: TemplateAttributeBindingUpdateRequest,
    handler: FromDishka[UpdateTemplateAttributeBindingHandler],
    list_handler: FromDishka[ListTemplateBindingsHandler],
) -> TemplateAttributeBindingDetailResponse:
    command = build_update_command(
        request,
        UpdateTemplateAttributeBindingCommand,
        field_converters={
            "requirement_level": RequirementLevel,
        },
        binding_id=binding_id,
        template_id=template_id,
    )
    result: UpdateTemplateAttributeBindingResult = await handler.handle(command)

    # Re-fetch via list handler to get enriched attribute metadata.
    bindings = await list_handler.handle(
        ListTemplateBindingsQuery(template_id=template_id, offset=0, limit=1_000)
    )
    enriched = next((b for b in bindings.items if b.id == result.id), None)
    if enriched is not None:
        return TemplateAttributeBindingDetailResponse(
            id=enriched.id,
            template_id=enriched.template_id,
            attribute_id=enriched.attribute_id,
            sort_order=enriched.sort_order,
            requirement_level=enriched.requirement_level,
            filter_settings=enriched.filter_settings,
            attribute_code=enriched.attribute_code,
            attribute_name_i18n=enriched.attribute_name_i18n,
            attribute_data_type=enriched.attribute_data_type,
            attribute_ui_type=enriched.attribute_ui_type,
            attribute_level=enriched.attribute_level,
            attribute_is_filterable=enriched.attribute_is_filterable,
        )
    # Fallback: return basic fields if re-fetch didn't find the binding.
    return TemplateAttributeBindingDetailResponse(
        id=result.id,
        template_id=result.template_id,
        attribute_id=result.attribute_id,
        sort_order=result.sort_order,
        requirement_level=result.requirement_level,
        filter_settings=result.filter_settings,
    )


@attribute_template_router.delete(
    path="/{template_id}/attributes/{binding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unbind an attribute from a template",
    description="Remove a template-attribute binding.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def unbind_attribute(
    template_id: uuid.UUID,
    binding_id: uuid.UUID,
    handler: FromDishka[UnbindAttributeFromTemplateHandler],
) -> None:
    command = UnbindAttributeFromTemplateCommand(
        binding_id=binding_id,
        template_id=template_id,
    )
    await handler.handle(command)


@attribute_template_router.post(
    path="/{template_id}/attributes/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reorder bindings",
    description="Bulk-reorder attribute bindings within a template.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def reorder_bindings(
    template_id: uuid.UUID,
    request: TemplateBindingReorderRequest,
    handler: FromDishka[ReorderTemplateBindingsHandler],
) -> None:
    command = ReorderTemplateBindingsCommand(
        template_id=template_id,
        items=[
            BindingReorderItem(
                binding_id=item.binding_id,
                sort_order=item.sort_order,
            )
            for item in request.items
        ],
    )
    await handler.handle(command)
