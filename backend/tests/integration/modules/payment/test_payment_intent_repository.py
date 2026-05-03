"""Integration tests for PaymentIntentRepository."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.payment.domain.entities import PaymentIntent
from src.modules.payment.domain.value_objects import (
    PaymentIntentStatus,
    ProviderCode,
)
from src.modules.payment.infrastructure.repositories.payment_intent_repository import (
    PaymentIntentRepository,
)

pytestmark = pytest.mark.integration


def _intent(idem_key: str = "idemp-key-12345") -> PaymentIntent:
    intent = PaymentIntent.initiate(
        order_id=uuid.uuid4(),
        provider=ProviderCode.FAKE,
        amount=10_000,
        currency="RUB",
        idempotency_key=idem_key,
    )
    intent.clear_domain_events()
    return intent


async def test_add_and_get(db_session: AsyncSession) -> None:
    repo = PaymentIntentRepository(db_session)
    intent = _intent()
    await repo.add(intent)
    fetched = await repo.get(intent.id)
    assert fetched is not None
    assert fetched.id == intent.id
    assert fetched.status == PaymentIntentStatus.INITIATED


async def test_get_by_idempotency_key(db_session: AsyncSession) -> None:
    repo = PaymentIntentRepository(db_session)
    intent = _intent("idem-unique-1")
    await repo.add(intent)
    fetched = await repo.get_by_idempotency_key("idem-unique-1")
    assert fetched is not None and fetched.id == intent.id


async def test_idempotency_key_unique(db_session: AsyncSession) -> None:
    repo = PaymentIntentRepository(db_session)
    a = _intent("idem-dup-1")
    b = _intent("idem-dup-1")
    await repo.add(a)
    with pytest.raises(IntegrityError):
        await repo.add(b)


async def test_update_persists_status(db_session: AsyncSession) -> None:
    repo = PaymentIntentRepository(db_session)
    intent = _intent("idem-tx-1")
    await repo.add(intent)
    intent.authorize(provider_reference="ref-1", client_secret="cs-1")
    intent.capture()
    intent.clear_domain_events()
    await repo.update(intent)

    fetched = await repo.get(intent.id)
    assert fetched is not None
    assert fetched.status == PaymentIntentStatus.CAPTURED
    assert fetched.provider_reference == "ref-1"
