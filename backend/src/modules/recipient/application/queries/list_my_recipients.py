"""Query: list recipients owned by an identity."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.recipient.application.queries.get_recipient import (
    _to_read_model,
)
from src.modules.recipient.application.queries.read_models import (
    RecipientListPage,
)
from src.modules.recipient.infrastructure.models import RecipientModel


@dataclass(frozen=True)
class ListMyRecipientsQuery:
    identity_id: uuid.UUID
    include_archived: bool = False


class ListMyRecipientsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListMyRecipientsQuery) -> RecipientListPage:
        stmt = (
            select(RecipientModel)
            .where(RecipientModel.identity_id == query.identity_id)
            .order_by(RecipientModel.created_at.desc())
        )
        if not query.include_archived:
            stmt = stmt.where(RecipientModel.is_archived.is_(False))
        rows = (await self._session.execute(stmt)).scalars().all()
        return RecipientListPage(items=[_to_read_model(r) for r in rows])
