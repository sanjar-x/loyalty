"""TaskIQ scheduled tasks for the Cart bounded context (D1.1).

Currently a single Beat cron:

* ``cart_freeze_expiry_cron`` — every 5 minutes; unfreezes FROZEN
  carts whose ``frozen_until`` has elapsed (CHECKOUT_TTL_MINUTES=15
  in the domain). Emits :class:`CartUnfrozenEvent` with
  ``reason="freeze_ttl_expired"`` so future analytics consumers can
  split system-driven unfreezes from explicit cancel_checkout calls.
"""

from __future__ import annotations

import structlog
from dishka.integrations.taskiq import FromDishka, inject

from src.bootstrap.broker import broker
from src.modules.cart.infrastructure.services.freeze_expiry_canceller import (
    FreezeExpiryCanceller,
)

logger = structlog.get_logger(__name__)


@broker.task(
    queue="cart_cron",
    exchange="taskiq_rpc_exchange",
    routing_key="cart.cron.freeze_expiry",
    max_retries=1,
    retry_on_error=True,
    timeout=120,
    schedule=[
        {"cron": "*/5 * * * *", "schedule_id": "cart_freeze_expiry_every_5min"},
    ],
)
@inject
async def cart_freeze_expiry_cron(
    *,
    canceller: FromDishka[FreezeExpiryCanceller],
) -> dict:
    """Unfreeze every FROZEN cart whose checkout TTL elapsed."""
    unfrozen = await canceller.run()
    return {"unfrozen": unfrozen}


__all__ = ["cart_freeze_expiry_cron"]
