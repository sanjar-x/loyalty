"""FastAPI router for the pricing-variable registry."""

from __future__ import annotations

import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_current_identity_id,
)
from src.modules.pricing.application.commands.create_variable import (
    CreateVariableCommand,
    CreateVariableHandler,
)
from src.modules.pricing.application.commands.delete_variable import (
    DeleteVariableCommand,
    DeleteVariableHandler,
)
from src.modules.pricing.application.commands.update_variable import (
    UpdateVariableCommand,
    UpdateVariableHandler,
)
from src.modules.pricing.application.queries.variables import (
    GetVariableHandler,
    GetVariableQuery,
    ListVariablesHandler,
    ListVariablesQuery,
    VariableReadModel,
)
from src.modules.pricing.domain.value_objects import VariableScope
from src.modules.pricing.presentation.schemas import (
    CreateVariableRequest,
    CreateVariableResponse,
    UpdateVariableRequest,
    VariableListResponse,
    VariableResponse,
)

pricing_variable_router = APIRouter(
    prefix="/pricing/variables",
    tags=["Pricing Variables"],
    route_class=DishkaRoute,
)


def _to_response(model: VariableReadModel) -> VariableResponse:
    return VariableResponse(
        variable_id=model.variable_id,
        code=model.code,
        scope=model.scope,
        data_type=model.data_type,
        unit=model.unit,
        name=model.name,
        description=model.description,
        is_required=model.is_required,
        default_value=model.default_value,
        is_system=model.is_system,
        is_fx_rate=model.is_fx_rate,
        is_user_editable_at_runtime=model.is_user_editable_at_runtime,
        max_age_days=model.max_age_days,
        version_lock=model.version_lock,
        created_at=model.created_at,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
    )


@pricing_variable_router.get(
    "",
    response_model=VariableListResponse,
    summary="List pricing variables",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def list_variables(
    handler: FromDishka[ListVariablesHandler],
    scope: Annotated[VariableScope | None, Query()] = None,
    is_system: Annotated[bool | None, Query()] = None,
    is_fx_rate: Annotated[bool | None, Query()] = None,
    _identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> VariableListResponse:
    items = await handler.handle(
        ListVariablesQuery(scope=scope, is_system=is_system, is_fx_rate=is_fx_rate)
    )
    responses = [_to_response(m) for m in items]
    return VariableListResponse(items=responses, total=len(responses))


@pricing_variable_router.post(
    "",
    response_model=CreateVariableResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new pricing variable",
    dependencies=[Depends(RequirePermission(codename="pricing:admin"))],
)
async def create_variable(
    body: CreateVariableRequest,
    handler: FromDishka[CreateVariableHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> CreateVariableResponse:
    result = await handler.handle(
        CreateVariableCommand(
            code=body.code,
            scope=body.scope,
            data_type=body.data_type,
            unit=body.unit,
            name=body.name.model_dump(),
            description=body.description.model_dump() if body.description else None,
            is_required=body.is_required,
            default_value=body.default_value,
            is_system=body.is_system,
            is_fx_rate=body.is_fx_rate,
            max_age_days=body.max_age_days,
            actor_id=identity_id,
        )
    )
    return CreateVariableResponse(
        variable_id=result.variable_id,
        code=result.code,
        version_lock=result.version_lock,
    )


@pricing_variable_router.get(
    "/{variable_id}",
    response_model=VariableResponse,
    summary="Get a pricing variable by id",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def get_variable(
    variable_id: uuid.UUID,
    handler: FromDishka[GetVariableHandler],
    _identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> VariableResponse:
    model = await handler.handle(GetVariableQuery(variable_id=variable_id))
    return _to_response(model)


@pricing_variable_router.patch(
    "/{variable_id}",
    response_model=VariableResponse,
    summary="Update the mutable fields of a pricing variable",
    dependencies=[Depends(RequirePermission(codename="pricing:admin"))],
)
async def update_variable(
    variable_id: uuid.UUID,
    body: UpdateVariableRequest,
    update_handler: FromDishka[UpdateVariableHandler],
    get_handler: FromDishka[GetVariableHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> VariableResponse:
    immutable_attempts: dict[str, object] = {}
    if body.code is not None:
        immutable_attempts["code"] = body.code
    if body.scope is not None:
        immutable_attempts["scope"] = body.scope.value
    if body.data_type is not None:
        immutable_attempts["data_type"] = body.data_type.value
    if body.unit is not None:
        immutable_attempts["unit"] = body.unit
    if body.is_fx_rate is not None:
        immutable_attempts["is_fx_rate"] = body.is_fx_rate

    await update_handler.handle(
        UpdateVariableCommand(
            variable_id=variable_id,
            actor_id=identity_id,
            expected_version_lock=body.expected_version_lock,
            name=body.name.model_dump() if body.name else None,
            description=(body.description.model_dump() if body.description else None),
            is_required=body.is_required,
            default_value=body.default_value,
            default_value_provided=body.default_value_provided,
            max_age_days=body.max_age_days,
            max_age_days_provided=body.max_age_days_provided,
            immutable_attempts=immutable_attempts or None,
        )
    )
    model = await get_handler.handle(GetVariableQuery(variable_id=variable_id))
    return _to_response(model)


@pricing_variable_router.delete(
    "/{variable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a pricing variable (blocked while in use)",
    dependencies=[Depends(RequirePermission(codename="pricing:admin"))],
)
async def delete_variable(
    variable_id: uuid.UUID,
    handler: FromDishka[DeleteVariableHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> None:
    await handler.handle(
        DeleteVariableCommand(variable_id=variable_id, actor_id=identity_id)
    )
