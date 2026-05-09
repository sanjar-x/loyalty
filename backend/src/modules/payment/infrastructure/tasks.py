"""TaskIQ scheduled tasks for the Payment bounded context.

Currently registers a single Beat cron:

* ``payment_auth_expiry_cron`` — every 6 hours; fails AUTHORIZED
  PaymentIntents whose ``auth_expires_at`` has elapsed (Visa-стандарт
  hold = ``PAYMENT_AUTH_TTL_DAYS=7``). Emits :class:`PaymentFailedEvent`
  via the outbox so Order's ``PaymentFailedConsumer`` cancels the
  parent order with :class:`CancellationReason.SYSTEM_AUTH_EXPIRED`.
"""

from __future__ import annotations

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.broker import broker
from src.modules.payment.infrastructure.services.auth_expiry_canceller import (
    AuthExpiryCanceller,
)

logger = structlog.get_logger(__name__)


@broker.task(
    queue="payment_cron",
    exchange="taskiq_rpc_exchange",
    routing_key="payment.cron.auth_expiry",
    max_retries=1,
    retry_on_error=True,
    timeout=120,
    schedule=[
        {"cron": "0 */6 * * *", "schedule_id": "payment_auth_expiry_every_6h"},
    ],
)
@inject
async def payment_auth_expiry_cron(
    *,
    canceller: FromDishka[AuthExpiryCanceller],
    session: FromDishka[AsyncSession],
) -> dict:
    """Fail every AUTHORIZED PaymentIntent whose hold elapsed.

    The handler commits per-intent inside :class:`FailPaymentIntentHandler`
    (each ``await self._uow.commit()`` flushes outbox rows in the same
    transaction). The trailing ``session.commit()`` here is a no-op for
    the canceller's own session — kept for symmetry with order's cron
    tasks so future readers don't get surprised by a missing commit.
    """
    failed = await canceller.run()
    await session.commit()
    return {"failed": failed}


__all__ = ["payment_auth_expiry_cron"]
