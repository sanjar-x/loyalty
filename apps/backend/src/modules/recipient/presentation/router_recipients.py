"""Customer-facing Recipient endpoints (under ``/recipients``)."""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, Response, status

from src.api.dependencies.etag import attach_etag, parse_if_match
from src.modules.identity.presentation.dependencies import Auth
from src.modules.recipient.application.commands.archive_recipient import (
    ArchiveRecipientCommand,
    ArchiveRecipientHandler,
)
from src.modules.recipient.application.commands.create_recipient import (
    CreateRecipientCommand,
    CreateRecipientHandler,
)
from src.modules.recipient.application.commands.update_recipient import (
    UpdateRecipientCommand,
    UpdateRecipientHandler,
)
from src.modules.recipient.application.queries.get_recipient import (
    GetRecipientHandler,
    GetRecipientQuery,
)
from src.modules.recipient.application.queries.list_my_recipients import (
    ListMyRecipientsHandler,
    ListMyRecipientsQuery,
)
from src.modules.recipient.application.queries.read_models import (
    RecipientReadModel,
)
from src.modules.recipient.presentation.schemas import (
    CreateRecipientRequest,
    CreateRecipientResponse,
    RecipientListResponse,
    RecipientSchema,
    UpdateRecipientRequest,
)
from shared.exceptions import OptimisticLockError, PreconditionFailedError

recipient_router = APIRouter(
    prefix="/recipients",
    tags=["Recipients"],
    route_class=DishkaRoute,
)


def _serialize(model: RecipientReadModel) -> RecipientSchema:
    return RecipientSchema(
        recipient_id=model.recipient_id,
        full_name_ru=model.full_name_ru,
        full_name_lat=model.full_name_lat,
        phone=model.phone,
        email=model.email,
        passport_serial=model.passport_serial,
        passport_number=model.passport_number,
        passport_issue_date=model.passport_issue_date,
        birth_date=model.birth_date,
        inn=model.inn,
        validation_status=model.validation_status,
        validation_failed_reason=model.validation_failed_reason,
        is_archived=model.is_archived,
        created_at=model.created_at,
        updated_at=model.updated_at,
        version=model.version,
    )


@recipient_router.post(
    "",
    response_model=CreateRecipientResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recipient(
    body: CreateRecipientRequest,
    auth: Auth,
    handler: FromDishka[CreateRecipientHandler],
) -> CreateRecipientResponse:
    result = await handler.handle(
        CreateRecipientCommand(
            identity_id=auth.identity_id,
            full_name_ru=body.full_name_ru,
            full_name_lat=body.full_name_lat,
            phone=body.phone,
            email=body.email,
            passport_serial=body.passport_serial,
            passport_number=body.passport_number,
            passport_issue_date=body.passport_issue_date,
            birth_date=body.birth_date,
            inn=body.inn,
        )
    )
    return CreateRecipientResponse(recipient_id=result.recipient_id)


@recipient_router.get("", response_model=RecipientListResponse)
async def list_my_recipients(
    auth: Auth,
    handler: FromDishka[ListMyRecipientsHandler],
    include_archived: bool = Query(default=False),
) -> RecipientListResponse:
    page = await handler.handle(
        ListMyRecipientsQuery(
            identity_id=auth.identity_id,
            include_archived=include_archived,
        )
    )
    return RecipientListResponse(items=[_serialize(r) for r in page.items])


@recipient_router.get("/{recipient_id}", response_model=RecipientSchema)
async def get_recipient(
    recipient_id: uuid.UUID,
    response: Response,
    auth: Auth,
    handler: FromDishka[GetRecipientHandler],
) -> RecipientSchema:
    rm = await handler.handle(
        GetRecipientQuery(recipient_id=recipient_id, identity_id=auth.identity_id)
    )
    # D0.3 — strong ETag based on the aggregate's optimistic-lock
    # version. Frontend echoes this back as ``If-Match`` on PATCH.
    attach_etag(response, rm.version)
    return _serialize(rm)


@recipient_router.patch("/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_recipient(
    recipient_id: uuid.UUID,
    body: UpdateRecipientRequest,
    auth: Auth,
    handler: FromDishka[UpdateRecipientHandler],
    if_match_version: int | None = Depends(parse_if_match),
) -> None:
    """D0.3 — accepts ``If-Match: "v{N}"``. Mismatch → 412
    ``PRECONDITION_FAILED``. Header absent → legacy last-write-wins
    (no behaviour change for clients still on the old contract).
    """
    try:
        await handler.handle(
            UpdateRecipientCommand(
                recipient_id=recipient_id,
                identity_id=auth.identity_id,
                full_name_ru=body.full_name_ru,
                full_name_lat=body.full_name_lat,
                phone=body.phone,
                email=body.email,
                passport_serial=body.passport_serial,
                passport_number=body.passport_number,
                passport_issue_date=body.passport_issue_date,
                birth_date=body.birth_date,
                inn=body.inn,
                expected_version=if_match_version,
            )
        )
    except OptimisticLockError as exc:
        if if_match_version is not None:
            raise PreconditionFailedError(
                entity_type="Recipient",
                entity_id=recipient_id,
                expected_version=if_match_version,
                current_version=exc.details.get("actual_version"),
            ) from exc
        raise


@recipient_router.delete("/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_recipient(
    recipient_id: uuid.UUID,
    auth: Auth,
    handler: FromDishka[ArchiveRecipientHandler],
) -> None:
    await handler.handle(
        ArchiveRecipientCommand(recipient_id=recipient_id, identity_id=auth.identity_id)
    )
