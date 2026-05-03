"""Data Mapper for the PaymentIntent aggregate."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.payment.domain.entities import PaymentIntent
from src.modules.payment.domain.interfaces import IPaymentIntentRepository
from src.modules.payment.domain.value_objects import (
    PaymentIntentStatus,
    ProviderCode,
)
from src.modules.payment.infrastructure.models import PaymentIntentModel


class PaymentIntentRepository(IPaymentIntentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, intent: PaymentIntent) -> PaymentIntent:
        row = PaymentIntentModel(
            id=intent.id,
            order_id=intent.order_id,
            provider=intent.provider.value,
            amount=intent.amount,
            currency=intent.currency,
            status=intent.status.value,
            provider_reference=intent.provider_reference,
            client_secret=intent.client_secret,
            idempotency_key=intent.idempotency_key,
            failure_reason=intent.failure_reason,
            auth_expires_at=intent.auth_expires_at,
            version=intent.version,
            created_at=intent.created_at,
            updated_at=intent.updated_at,
        )
        self._session.add(row)
        await self._session.flush()
        return intent

    async def get(self, intent_id: uuid.UUID) -> PaymentIntent | None:
        stmt = select(PaymentIntentModel).where(PaymentIntentModel.id == intent_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def get_for_update(self, intent_id: uuid.UUID) -> PaymentIntent | None:
        stmt = (
            select(PaymentIntentModel)
            .where(PaymentIntentModel.id == intent_id)
            .with_for_update()
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def get_by_idempotency_key(self, key: str) -> PaymentIntent | None:
        stmt = select(PaymentIntentModel).where(
            PaymentIntentModel.idempotency_key == key
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def update(self, intent: PaymentIntent) -> PaymentIntent:
        stmt = select(PaymentIntentModel).where(PaymentIntentModel.id == intent.id)
        row = (await self._session.execute(stmt)).scalar_one()
        row.status = intent.status.value
        row.provider_reference = intent.provider_reference
        row.client_secret = intent.client_secret
        row.failure_reason = intent.failure_reason
        row.auth_expires_at = intent.auth_expires_at
        row.version = intent.version + 1
        row.updated_at = intent.updated_at
        await self._session.flush()
        return intent


def _to_domain(row: PaymentIntentModel) -> PaymentIntent:
    return PaymentIntent(
        id=row.id,
        order_id=row.order_id,
        provider=ProviderCode(row.provider),
        amount=row.amount,
        currency=row.currency,
        status=PaymentIntentStatus(row.status),
        provider_reference=row.provider_reference,
        client_secret=row.client_secret,
        idempotency_key=row.idempotency_key,
        failure_reason=row.failure_reason,
        auth_expires_at=row.auth_expires_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version,
    )
