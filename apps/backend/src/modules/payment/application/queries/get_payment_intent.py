"""Query: fetch a PaymentIntent by id (read-side ORM access)."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.payment.domain.exceptions import PaymentIntentNotFoundError
from src.modules.payment.infrastructure.models import PaymentIntentModel


@dataclass(frozen=True)
class PaymentIntentReadModel:
    intent_id: uuid.UUID
    order_id: uuid.UUID
    provider: str
    amount: int
    currency: str
    status: str
    provider_reference: str | None
    client_secret: str | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class GetPaymentIntentQuery:
    intent_id: uuid.UUID


class GetPaymentIntentHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetPaymentIntentQuery) -> PaymentIntentReadModel:
        stmt = select(PaymentIntentModel).where(
            PaymentIntentModel.id == query.intent_id
        )
        row: PaymentIntentModel | None = (
            await self._session.execute(stmt)
        ).scalar_one_or_none()
        if row is None:
            raise PaymentIntentNotFoundError(intent_id=str(query.intent_id))
        return PaymentIntentReadModel(
            intent_id=row.id,
            order_id=row.order_id,
            provider=row.provider,
            amount=row.amount,
            currency=row.currency,
            status=row.status,
            provider_reference=row.provider_reference,
            client_secret=row.client_secret,
            failure_reason=row.failure_reason,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
