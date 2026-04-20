"""FastAPI router for formula-version endpoints (FRD §Formulas API)."""

from __future__ import annotations

import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_current_identity_id,
)
from src.modules.pricing.application.commands.discard_formula_draft import (
    DiscardFormulaDraftCommand,
    DiscardFormulaDraftHandler,
)
from src.modules.pricing.application.commands.publish_formula_draft import (
    PublishFormulaDraftCommand,
    PublishFormulaDraftHandler,
)
from src.modules.pricing.application.commands.rollback_formula import (
    RollbackFormulaCommand,
    RollbackFormulaHandler,
)
from src.modules.pricing.application.commands.upsert_formula_draft import (
    UpsertFormulaDraftCommand,
    UpsertFormulaDraftHandler,
)
from src.modules.pricing.application.queries.formulas import (
    FormulaVersionReadModel,
    GetFormulaDraftHandler,
    GetFormulaDraftQuery,
    GetFormulaVersionHandler,
    GetFormulaVersionQuery,
    ListFormulaVersionsHandler,
    ListFormulaVersionsQuery,
)
from src.modules.pricing.domain.value_objects import FormulaStatus
from src.modules.pricing.presentation.schemas import (
    DiscardFormulaDraftResponse,
    FormulaVersionListResponse,
    FormulaVersionResponse,
    PublishFormulaResponse,
    RollbackFormulaResponse,
    UpsertFormulaDraftRequest,
    UpsertFormulaDraftResponse,
)

pricing_formula_router = APIRouter(
    prefix="/pricing/contexts/{context_id}/formula",
    tags=["Pricing Formulas"],
    route_class=DishkaRoute,
)


def _to_response(model: FormulaVersionReadModel) -> FormulaVersionResponse:
    return FormulaVersionResponse(
        version_id=model.version_id,
        context_id=model.context_id,
        version_number=model.version_number,
        status=model.status,
        ast=model.ast,
        published_at=model.published_at,
        published_by=model.published_by,
        version_lock=model.version_lock,
        created_at=model.created_at,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
    )


@pricing_formula_router.get(
    "/versions",
    response_model=FormulaVersionListResponse,
    summary="List formula versions for a context",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def list_versions(
    context_id: uuid.UUID,
    handler: FromDishka[ListFormulaVersionsHandler],
    status_filter: Annotated[FormulaStatus | None, Query(alias="status")] = None,
    _identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> FormulaVersionListResponse:
    items = await handler.handle(
        ListFormulaVersionsQuery(context_id=context_id, status=status_filter)
    )
    responses = [_to_response(m) for m in items]
    return FormulaVersionListResponse(items=responses, total=len(responses))


@pricing_formula_router.get(
    "/versions/{version_id}",
    response_model=FormulaVersionResponse,
    summary="Get a formula version by id",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def get_version(
    context_id: uuid.UUID,
    version_id: uuid.UUID,
    handler: FromDishka[GetFormulaVersionHandler],
    _identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> FormulaVersionResponse:
    model = await handler.handle(GetFormulaVersionQuery(version_id=version_id))
    return _to_response(model)


@pricing_formula_router.get(
    "/draft",
    response_model=FormulaVersionResponse,
    summary="Get the current draft for a context",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def get_draft(
    context_id: uuid.UUID,
    handler: FromDishka[GetFormulaDraftHandler],
    _identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> FormulaVersionResponse:
    model = await handler.handle(GetFormulaDraftQuery(context_id=context_id))
    return _to_response(model)


@pricing_formula_router.put(
    "/draft",
    response_model=UpsertFormulaDraftResponse,
    summary="Create or overwrite the draft formula for a context",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def upsert_draft(
    context_id: uuid.UUID,
    body: UpsertFormulaDraftRequest,
    handler: FromDishka[UpsertFormulaDraftHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> UpsertFormulaDraftResponse:
    result = await handler.handle(
        UpsertFormulaDraftCommand(
            context_id=context_id,
            ast=body.ast,
            actor_id=identity_id,
            expected_version_lock=body.expected_version_lock,
        )
    )
    return UpsertFormulaDraftResponse(
        version_id=result.version_id,
        version_number=result.version_number,
        version_lock=result.version_lock,
        created=result.created,
    )


@pricing_formula_router.delete(
    "/draft",
    response_model=DiscardFormulaDraftResponse,
    summary="Discard the current draft",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def discard_draft(
    context_id: uuid.UUID,
    handler: FromDishka[DiscardFormulaDraftHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> DiscardFormulaDraftResponse:
    result = await handler.handle(
        DiscardFormulaDraftCommand(context_id=context_id, actor_id=identity_id)
    )
    return DiscardFormulaDraftResponse(version_id=result.version_id)


@pricing_formula_router.post(
    "/draft/publish",
    response_model=PublishFormulaResponse,
    status_code=status.HTTP_200_OK,
    summary="Publish the current draft",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def publish_draft(
    context_id: uuid.UUID,
    handler: FromDishka[PublishFormulaDraftHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> PublishFormulaResponse:
    result = await handler.handle(
        PublishFormulaDraftCommand(context_id=context_id, actor_id=identity_id)
    )
    return PublishFormulaResponse(
        version_id=result.version_id,
        version_number=result.version_number,
        previous_version_id=result.previous_version_id,
    )


@pricing_formula_router.post(
    "/versions/{version_id}/rollback",
    response_model=RollbackFormulaResponse,
    status_code=status.HTTP_200_OK,
    summary="Rollback to a previously-archived version",
    dependencies=[Depends(RequirePermission(codename="pricing:manage"))],
)
async def rollback_version(
    context_id: uuid.UUID,
    version_id: uuid.UUID,
    handler: FromDishka[RollbackFormulaHandler],
    identity_id: uuid.UUID = Depends(get_current_identity_id),
) -> RollbackFormulaResponse:
    result = await handler.handle(
        RollbackFormulaCommand(
            context_id=context_id,
            target_version_id=version_id,
            actor_id=identity_id,
        )
    )
    return RollbackFormulaResponse(
        version_id=result.version_id,
        rolled_back_from_version_id=result.rolled_back_from_version_id,
    )
