"""Admin-scope Passport endpoints (under ``/admin/passports``).

Read-only — admin never creates / updates / archives a passport on
behalf of the customer (ADR-011 § I2: customer owns customs PII).
Required so the admin walk-in form can render a passport selector
for cross-border orders without violating the per-customer JWT scope
of ``/api/v1/passports`` (which is owner-only by construction).

If a walk-in customer has zero passports on file, the admin tells
them to add one via the mini-app — this endpoint surfaces that state
as an empty list rather than a 404, which lets the admin UI render a
"customer has no passport yet" empty state without branching on HTTP
status.
"""

from __future__ import annotations

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query

from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    RequireStaffRole,
)
from src.modules.passport.application.queries.list_my_passports import (
    ListMyPassportsHandler,
    ListMyPassportsQuery,
)
from src.modules.passport.application.queries.read_models import PassportReadModel
from src.modules.passport.presentation.schemas import (
    PassportListResponse,
    PassportSchema,
)

admin_passport_router = APIRouter(
    prefix="/admin/passports",
    tags=["Admin / Passport"],
    dependencies=[Depends(RequireStaffRole)],
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


@admin_passport_router.get(
    "",
    response_model=PassportListResponse,
    dependencies=[Depends(RequirePermission("passport:read"))],
)
async def admin_list_passports(
    handler: FromDishka[ListMyPassportsHandler],
    identity_id: uuid.UUID = Query(alias="identityId"),
    include_archived: bool = Query(default=False, alias="includeArchived"),
) -> PassportListResponse:
    """List passports owned by a specific customer (admin walk-in selector).

    Returns ``200`` with an empty list when ``identityId`` matches no
    passports — admin UI uses the same empty state for «customer has no
    passport yet» and «no such identity», avoiding a 404 branch on a
    selector that is allowed to be empty.

    ``includeArchived`` defaults to ``false`` so the selector never
    surfaces soft-deleted rows by accident; pass ``true`` from the
    admin audit view if needed.
    """
    page = await handler.handle(
        ListMyPassportsQuery(
            identity_id=identity_id,
            include_archived=include_archived,
        )
    )
    return PassportListResponse(items=[_serialize(r) for r in page.items])
