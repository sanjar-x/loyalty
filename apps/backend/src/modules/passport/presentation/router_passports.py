"""Customer-facing Passport endpoints (under ``/passports``).

Ownership is enforced inside each handler / query via
``identity_id == auth.identity_id``. Endpoints intentionally do NOT
return other customers' passports — list endpoint is scoped to «my
passports» by construction.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Path, Query, status

from src.modules.identity.presentation.dependencies import Auth
from src.modules.passport.application.commands.archive_passport import (
    ArchivePassportCommand,
    ArchivePassportHandler,
)
from src.modules.passport.application.commands.create_passport import (
    CreatePassportCommand,
    CreatePassportHandler,
)
from src.modules.passport.application.commands.update_passport import (
    UpdatePassportCommand,
    UpdatePassportHandler,
)
from src.modules.passport.application.queries.get_passport import (
    GetPassportHandler,
    GetPassportQuery,
)
from src.modules.passport.application.queries.list_my_passports import (
    ListMyPassportsHandler,
    ListMyPassportsQuery,
)
from src.modules.passport.application.queries.read_models import PassportReadModel
from src.modules.passport.presentation.schemas import (
    CreatePassportRequest,
    CreatePassportResponse,
    PassportListResponse,
    PassportSchema,
    UpdatePassportRequest,
)

passport_router = APIRouter(
    prefix="/passports",
    tags=["Passports"],
    route_class=DishkaRoute,
)


def _serialize(rm: PassportReadModel) -> PassportSchema:
    return PassportSchema(
        passport_id=rm.passport_id,
        full_name_ru=rm.full_name_ru,
        full_name_lat=rm.full_name_lat,
        passport_serial=rm.passport_serial,
        passport_number=rm.passport_number,
        passport_issue_date=rm.passport_issue_date,
        birth_date=rm.birth_date,
        inn=rm.inn,
        validation_status=rm.validation_status,
        validation_failed_reason=rm.validation_failed_reason,
        is_archived=rm.is_archived,
        created_at=rm.created_at,
        updated_at=rm.updated_at,
        version=rm.version,
    )


@passport_router.post(
    "",
    response_model=CreatePassportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_passport(
    body: CreatePassportRequest,
    auth: Auth,
    handler: FromDishka[CreatePassportHandler],
) -> CreatePassportResponse:
    result = await handler.handle(
        CreatePassportCommand(
            identity_id=auth.identity_id,
            full_name_ru=body.full_name_ru,
            full_name_lat=body.full_name_lat,
            passport_serial=body.passport_serial,
            passport_number=body.passport_number,
            passport_issue_date=body.passport_issue_date,
            birth_date=body.birth_date,
            inn=body.inn,
        )
    )
    return CreatePassportResponse(passport_id=result.passport_id)


@passport_router.get("", response_model=PassportListResponse)
async def list_my_passports(
    auth: Auth,
    handler: FromDishka[ListMyPassportsHandler],
    include_archived: bool = Query(default=False, alias="includeArchived"),
) -> PassportListResponse:
    page = await handler.handle(
        ListMyPassportsQuery(
            identity_id=auth.identity_id,
            include_archived=include_archived,
        )
    )
    return PassportListResponse(items=[_serialize(r) for r in page.items])


@passport_router.get("/{passportId}", response_model=PassportSchema)
async def get_passport(
    passport_id: Annotated[uuid.UUID, Path(alias="passportId")],
    auth: Auth,
    handler: FromDishka[GetPassportHandler],
) -> PassportSchema:
    rm = await handler.handle(
        GetPassportQuery(passport_id=passport_id, identity_id=auth.identity_id)
    )
    return _serialize(rm)


@passport_router.patch("/{passportId}", status_code=status.HTTP_204_NO_CONTENT)
async def update_passport(
    passport_id: Annotated[uuid.UUID, Path(alias="passportId")],
    body: UpdatePassportRequest,
    auth: Auth,
    handler: FromDishka[UpdatePassportHandler],
) -> None:
    await handler.handle(
        UpdatePassportCommand(
            passport_id=passport_id,
            identity_id=auth.identity_id,
            full_name_ru=body.full_name_ru,
            full_name_lat=body.full_name_lat,
            passport_serial=body.passport_serial,
            passport_number=body.passport_number,
            passport_issue_date=body.passport_issue_date,
            birth_date=body.birth_date,
            inn=body.inn,
        )
    )


@passport_router.delete("/{passportId}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_passport(
    passport_id: Annotated[uuid.UUID, Path(alias="passportId")],
    auth: Auth,
    handler: FromDishka[ArchivePassportHandler],
) -> None:
    """Archive (soft-delete) a passport.

    Orders that reference the archived passport retain their
    ``passport_snapshot`` JSONB — history is preserved. ``passport_id``
    FK on orders is ``ON DELETE SET NULL`` for safety, but archive
    does NOT actually delete the row; only ``is_archived=true``.
    """
    await handler.handle(
        ArchivePassportCommand(
            passport_id=passport_id,
            identity_id=auth.identity_id,
        )
    )
