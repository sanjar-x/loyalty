"""Integration tests for the auth-expiry cron pipeline (B3).

Covers the full chain inside a single PG transaction:

1. Selector picks only AUTHORIZED intents whose ``auth_expires_at`` is past.
2. ``AuthExpiryCanceller`` drives ``FailPaymentIntentHandler`` per intent
   so each one transitions to FAILED with ``failure_reason="auth_expired"``.
3. ``PaymentFailedEvent`` lands in ``outbox_messages`` (via UoW commit).
4. The outbox payload carries ``reason="auth_expired"`` so Order's
   ``PaymentFailedConsumer`` can pick the SYSTEM_AUTH_EXPIRED branch.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.outbox import OutboxMessage
from src.infrastructure.database.uow import UnitOfWork
from src.modules.payment.application.commands.fail_payment_intent import (
    FailPaymentIntentHandler,
)
from src.modules.payment.domain.entities import PaymentIntent
from src.modules.payment.domain.value_objects import (
    PaymentIntentStatus,
    ProviderCode,
)
from src.modules.payment.infrastructure.repositories.payment_intent_repository import (
    PaymentIntentRepository,
)
from src.modules.payment.infrastructure.services.auth_expiry_canceller import (
    AUTH_EXPIRED_REASON,
    AuthExpiryCanceller,
)

pytestmark = pytest.mark.integration


def _stdlib_logger() -> logging.Logger:
    """A real logger with a ``bind`` method that's tolerant of kwargs."""

    class _BoundAdapter:
        def __init__(self, base: logging.Logger) -> None:
            self._base = base

        def bind(self, **_: object) -> _BoundAdapter:
            return self

        def info(self, *args: object, **kwargs: object) -> None:
            self._base.info(args[0] if args else "", extra=kwargs)

        def warning(self, *args: object, **kwargs: object) -> None:
            self._base.warning(args[0] if args else "", extra=kwargs)

        def exception(self, *args: object, **kwargs: object) -> None:
            self._base.exception(args[0] if args else "", extra=kwargs)

        def error(self, *args: object, **kwargs: object) -> None:
            self._base.error(args[0] if args else "", extra=kwargs)

        def debug(self, *args: object, **kwargs: object) -> None:
            self._base.debug(args[0] if args else "", extra=kwargs)

    return _BoundAdapter(logging.getLogger("test.auth_expiry"))  # ty: ignore[invalid-return-type]


async def _make_authorized_intent(
    session: AsyncSession,
    *,
    auth_expires_at: datetime | None,
    idempotency_key: str,
) -> PaymentIntent:
    """Persist a PaymentIntent in AUTHORIZED with the given expiry."""
    repo = PaymentIntentRepository(session)
    intent = PaymentIntent.initiate(
        order_id=uuid.uuid4(),
        provider=ProviderCode.FAKE,
        amount=12_345,
        currency="RUB",
        idempotency_key=idempotency_key,
    )
    intent.clear_domain_events()
    await repo.add(intent)
    intent.authorize(
        provider_reference=f"prov_ref_{idempotency_key}",
        client_secret=f"cs_{idempotency_key}",
        auth_expires_at=auth_expires_at,
    )
    intent.clear_domain_events()
    await repo.update(intent)
    await session.flush()
    return intent


async def test_selector_returns_only_expired_authorized(
    db_session: AsyncSession,
) -> None:
    repo = PaymentIntentRepository(db_session)
    now = datetime.now(UTC)

    expired = await _make_authorized_intent(
        db_session,
        auth_expires_at=now - timedelta(hours=1),
        idempotency_key="auth-expired-1",
    )
    fresh = await _make_authorized_intent(
        db_session,
        auth_expires_at=now + timedelta(days=3),
        idempotency_key="auth-fresh-1",
    )
    no_expiry = await _make_authorized_intent(
        db_session,
        auth_expires_at=None,
        idempotency_key="auth-no-expiry-1",
    )

    expired_ids = await repo.find_expired_authorized(now=now, limit=10)

    assert expired.id in expired_ids
    assert fresh.id not in expired_ids
    assert no_expiry.id not in expired_ids


async def test_selector_skips_terminal_intents(db_session: AsyncSession) -> None:
    repo = PaymentIntentRepository(db_session)
    now = datetime.now(UTC)

    intent = await _make_authorized_intent(
        db_session,
        auth_expires_at=now - timedelta(hours=2),
        idempotency_key="captured-then-expired",
    )
    intent.capture()
    intent.clear_domain_events()
    await repo.update(intent)
    await db_session.flush()

    expired_ids = await repo.find_expired_authorized(now=now, limit=10)
    assert intent.id not in expired_ids


async def test_canceller_fails_expired_and_writes_outbox_event(
    db_session: AsyncSession,
) -> None:
    repo = PaymentIntentRepository(db_session)
    now = datetime.now(UTC)

    intent = await _make_authorized_intent(
        db_session,
        auth_expires_at=now - timedelta(hours=1),
        idempotency_key="cron-cancel-1",
    )

    uow = UnitOfWork(db_session)
    fail_handler = FailPaymentIntentHandler(
        repo=repo,
        uow=uow,
        logger=_stdlib_logger(),  # ty: ignore[invalid-argument-type]
    )
    canceller = AuthExpiryCanceller(repo, fail_handler, _stdlib_logger())  # ty: ignore[invalid-argument-type]

    failed = await canceller.run()

    assert failed == 1
    refreshed = await repo.get(intent.id)
    assert refreshed is not None
    assert refreshed.status == PaymentIntentStatus.FAILED
    assert refreshed.failure_reason == AUTH_EXPIRED_REASON

    # Outbox row was written atomically with the intent.fail() commit.
    rows = (
        (
            await db_session.execute(
                select(OutboxMessage).where(
                    OutboxMessage.aggregate_id == str(intent.id),
                    OutboxMessage.event_type == "PaymentFailedEvent",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].payload.get("reason") == AUTH_EXPIRED_REASON
    assert rows[0].payload.get("order_id") == str(intent.order_id)


async def test_canceller_idempotent_on_already_failed_intent(
    db_session: AsyncSession,
) -> None:
    """Second tick on the same expired intent is a no-op (terminal early return)."""
    repo = PaymentIntentRepository(db_session)
    now = datetime.now(UTC)

    await _make_authorized_intent(
        db_session,
        auth_expires_at=now - timedelta(hours=1),
        idempotency_key="cron-idempotent-1",
    )

    uow = UnitOfWork(db_session)
    fail_handler = FailPaymentIntentHandler(
        repo=repo,
        uow=uow,
        logger=_stdlib_logger(),  # ty: ignore[invalid-argument-type]
    )
    canceller = AuthExpiryCanceller(repo, fail_handler, _stdlib_logger())  # ty: ignore[invalid-argument-type]

    first = await canceller.run()
    assert first == 1
    second = await canceller.run()
    # Selector now filters this out because status==FAILED.
    assert second == 0
