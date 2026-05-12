"""TaskIQ tasks + outbox dispatchers for the referral module.

Phase 1 wires only the identity-event consumers (issue-code on signup).
Order-event consumers (activation / refund / lifetime share) and the
cron jobs are added in subsequent PRs.

Idempotency: every consumer is wrapped in
:func:`run_inbox_idempotent` so duplicate broker deliveries become
no-ops at the business-effect level.
"""

from __future__ import annotations

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.broker import broker
from src.infrastructure.idempotency.runner import run_inbox_idempotent
from src.infrastructure.outbox.relay import register_event_handler
from src.modules.referral.application.consumers.identity_events import (
    IssueCodeOnIdentityRegisteredConsumer,
    IssueCodeOnLinkedAccountCreatedConsumer,
)
from shared.interfaces.idempotency import IInboxStore

logger = structlog.get_logger(__name__)


def _labels(correlation_id: str | None) -> dict[str, str]:
    return {"correlation_id": correlation_id} if correlation_id else {}


# ---------------------------------------------------------------------------
# Identity-event TaskIQ consumers
# ---------------------------------------------------------------------------


@broker.task(
    queue="referral_consumers",
    exchange="taskiq_rpc_exchange",
    routing_key="referral.identity.registered",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def referral_on_identity_registered(
    payload: dict,
    *,
    consumer: FromDishka[IssueCodeOnIdentityRegisteredConsumer],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="referral.IdentityRegistered",
        inbox=inbox,
        session=session,
        body=lambda: consumer.handle(payload),
    )


@broker.task(
    queue="referral_consumers",
    exchange="taskiq_rpc_exchange",
    routing_key="referral.linked_account.created",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def referral_on_linked_account_created(
    payload: dict,
    *,
    consumer: FromDishka[IssueCodeOnLinkedAccountCreatedConsumer],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="referral.LinkedAccountCreated",
        inbox=inbox,
        session=session,
        body=lambda: consumer.handle(payload),
    )


# ---------------------------------------------------------------------------
# Outbox dispatchers
# ---------------------------------------------------------------------------


async def _on_identity_registered(
    payload: dict, correlation_id: str | None = None
) -> None:
    await (
        referral_on_identity_registered.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


async def _on_linked_account_created(
    payload: dict, correlation_id: str | None = None
) -> None:
    await (
        referral_on_linked_account_created.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


register_event_handler("IdentityRegisteredEvent", _on_identity_registered)
register_event_handler("LinkedAccountCreatedEvent", _on_linked_account_created)
