"""FastAPI router for the pricing-context registry (FRD §Contexts)."""

from __future__ import annotations

import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_current_identity_id,
)
from src.modules.pricing.application.commands.create_context import (
    CreateContextCommand,
    CreateContextHandler,
)
from src.modules.pricing.application.commands.deactivate_context import (
    DeactivateContextCommand,
    DeactivateContextHandler,
)
from src.modules.pricing.application.commands.freeze_context import (
    FreezeContextCommand,
    FreezeContextHandler,
)
from src.modules.pricing.application.commands.unfreeze_context import (
    UnfreezeContextCommand,
    UnfreezeContextHandler,
)
from src.modules.pricing.application.commands.update_context import (
    UpdateContextCommand,
    UpdateContextHandler,
)
from src.modules.pricing.application.queries.contexts import (
    GetContextHandler,
    GetContextQuery,
    ListContextsHandler,
    ListContextsQuery,
    PricingContextReadModel,
)
from src.modules.pricing.presentation.schemas import (
    ContextListResponse,
    CreateContextRequest,
    CreateContextResponse,
    FreezeContextRequest,
    MutateContextResponse,
    PricingContextResponse,
    UpdateContextRequest,
)

pricing_context_router = APIRouter(
    prefix="/pricing/contexts",
    tags=["Pricing Contexts"],
    route_class=DishkaRoute,
)


def _to_response(model: PricingContextReadModel) -> PricingContextResponse:
    return PricingContextResponse(
        context_id=model.context_id,
        code=model.code,
        name=model.name,
        is_active=model.is_active,
        is_frozen=model.is_frozen,
        freeze_reason=model.freeze_reason,
        rounding_mode=model.rounding_mode,
        rounding_step=model.rounding_step,
        margin_floor_pct=model.margin_floor_pct,
        evaluation_timeout_ms=model.evaluation_timeout_ms,
        simulation_threshold=model.simulation_threshold,
        approval_required_on_publish=model.approval_required_on_publish,
        range_base_variable_code=model.range_base_variable_code,
        active_formula_version_id=model.active_formula_version_id,
        version_lock=model.version_lock,
        created_at=model.created_at,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
    )


@pricing_context_router.get(
    "",
    response_model=ContextListResponse,
    summary="List pricing contexts",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def list_contexts(
    handler: FromDishka[ListContextsHandler],
    is_active: Annotated[bool | None, Query()] = None,
    is_frozen: Annotated[bool | None, Query()] = None,
    _identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> ContextListResponse:
    items = await handler.handle(
        ListContextsQuery(is_active=is_active, is_frozen=is_frozen)
    )
    responses = [_to_response(m) for m in items]
    return ContextListResponse(items=responses, total=len(responses))


@pricing_context_router.post(
    "",
    response_model=CreateContextResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pricing context",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def create_context(
    body: CreateContextRequest,
    handler: FromDishka[CreateContextHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> CreateContextResponse:
    result = await handler.handle(
        CreateContextCommand(
            code=body.code,
            name=body.name.model_dump(),
            rounding_mode=body.rounding_mode,
            rounding_step=body.rounding_step,
            margin_floor_pct=body.margin_floor_pct,
            evaluation_timeout_ms=body.evaluation_timeout_ms,
            simulation_threshold=body.simulation_threshold,
            approval_required_on_publish=body.approval_required_on_publish,
            range_base_variable_code=body.range_base_variable_code,
            actor_id=identity_id,
        )
    )
    return CreateContextResponse(
        context_id=result.context_id,
        code=result.code,
        version_lock=result.version_lock,
    )


@pricing_context_router.get(
    "/{context_id}",
    response_model=PricingContextResponse,
    summary="Get a pricing context by id",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def get_context(
    context_id: uuid.UUID,
    handler: FromDishka[GetContextHandler],
    _identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> PricingContextResponse:
    model = await handler.handle(GetContextQuery(context_id=context_id))
    return _to_response(model)


@pricing_context_router.patch(
    "/{context_id}",
    response_model=PricingContextResponse,
    summary="Update mutable fields of a pricing context",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def update_context(
    context_id: uuid.UUID,
    body: UpdateContextRequest,
    update_handler: FromDishka[UpdateContextHandler],
    get_handler: FromDishka[GetContextHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> PricingContextResponse:
    immutable_attempts: dict[str, object] = {}
    if body.code is not None:
        immutable_attempts["code"] = body.code

    await update_handler.handle(
        UpdateContextCommand(
            context_id=context_id,
            actor_id=identity_id,
            expected_version_lock=body.expected_version_lock,
            name=body.name.model_dump() if body.name else None,
            rounding_mode=body.rounding_mode,
            rounding_step=body.rounding_step,
            margin_floor_pct=body.margin_floor_pct,
            evaluation_timeout_ms=body.evaluation_timeout_ms,
            simulation_threshold=body.simulation_threshold,
            approval_required_on_publish=body.approval_required_on_publish,
            range_base_variable_code=body.range_base_variable_code,
            range_base_variable_code_provided=body.range_base_variable_code_provided,
            immutable_attempts=immutable_attempts or None,
        )
    )
    model = await get_handler.handle(GetContextQuery(context_id=context_id))
    return _to_response(model)


@pricing_context_router.delete(
    "/{context_id}",
    response_model=MutateContextResponse,
    summary="Soft-deactivate a pricing context",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def deactivate_context(
    context_id: uuid.UUID,
    handler: FromDishka[DeactivateContextHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> MutateContextResponse:
    result = await handler.handle(
        DeactivateContextCommand(context_id=context_id, actor_id=identity_id)
    )
    return MutateContextResponse(
        context_id=result.context_id, version_lock=result.version_lock
    )


@pricing_context_router.post(
    "/{context_id}/freeze",
    response_model=MutateContextResponse,
    summary="Freeze a pricing context (emergency kill-switch)",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def freeze_context(
    context_id: uuid.UUID,
    body: FreezeContextRequest,
    handler: FromDishka[FreezeContextHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> MutateContextResponse:
    result = await handler.handle(
        FreezeContextCommand(
            context_id=context_id,
            reason=body.reason,
            actor_id=identity_id,
        )
    )
    return MutateContextResponse(
        context_id=result.context_id, version_lock=result.version_lock
    )


@pricing_context_router.post(
    "/{context_id}/unfreeze",
    response_model=MutateContextResponse,
    summary="Unfreeze a pricing context",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def unfreeze_context(
    context_id: uuid.UUID,
    handler: FromDishka[UnfreezeContextHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> MutateContextResponse:
    result = await handler.handle(
        UnfreezeContextCommand(context_id=context_id, actor_id=identity_id)
    )
    return MutateContextResponse(
        context_id=result.context_id, version_lock=result.version_lock
    )
