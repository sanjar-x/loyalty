"""Query: get a single recipient by id (ownership-scoped)."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.recipient.application.queries.read_models import (
    RecipientReadModel,
)
from src.modules.recipient.domain.exceptions import RecipientNotFoundError
from src.modules.recipient.infrastructure.models import RecipientModel


@dataclass(frozen=True)
class GetRecipientQuery:
    recipient_id: uuid.UUID
    identity_id: uuid.UUID


class GetRecipientHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetRecipientQuery) -> RecipientReadModel:
        stmt = (
            select(RecipientModel)
            .where(RecipientModel.id == query.recipient_id)
            .where(RecipientModel.identity_id == query.identity_id)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise RecipientNotFoundError(recipient_id=str(query.recipient_id))
        return _to_read_model(row)


def _to_read_model(row: RecipientModel) -> RecipientReadModel:
    return RecipientReadModel(
        recipient_id=row.id,
        full_name_ru=row.full_name_ru,
        full_name_lat=row.full_name_lat,
        phone=row.phone,
        email=row.email,
        passport_serial=row.passport_serial,
        passport_number=row.passport_number,
        passport_issue_date=row.passport_issue_date,
        birth_date=row.birth_date,
        inn=row.inn,
        validation_status=row.validation_status,
        validation_failed_reason=row.validation_failed_reason,
        is_archived=row.is_archived,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
