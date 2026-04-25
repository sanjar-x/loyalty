"""TaskIQ scheduled tasks for Outbox Relay and Pruning.

Relay: polls ``outbox_messages`` every minute via TaskIQ Beat.
Pruning: daily cleanup of processed records older than 7 days (03:00 UTC).
"""

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.broker import broker
from src.infrastructure.outbox.relay import (
    prune_processed_messages,
    register_event_handler,
    relay_outbox_batch,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Event handler registration (event_type -> TaskIQ dispatch)
# ---------------------------------------------------------------------------


def _build_labels(correlation_id: str | None) -> dict[str, str]:
    """Build TaskIQ labels for end-to-end tracing (HTTP -> Outbox -> TaskIQ).

    Args:
        correlation_id: The correlation ID from the outbox event, if available.

    Returns:
        A labels dict containing the correlation_id, or an empty dict.
    """
    if correlation_id:
        return {"correlation_id": correlation_id}
    return {}


# ---------------------------------------------------------------------------
# IAM event handlers
# ---------------------------------------------------------------------------


async def _handle_identity_registered(
    payload: dict, correlation_id: str | None = None
) -> None:
    """Dispatches profile creation consumer (Customer or StaffMember)."""
    from src.modules.user.application.consumers.identity_events import (
        create_profile_on_identity_registered,
    )

    await (
        create_profile_on_identity_registered.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(
            identity_id=payload["identity_id"],
            email=payload["email"],
        )  # ty:ignore[no-matching-overload]
    )


async def _handle_identity_deactivated(
    payload: dict, correlation_id: str | None = None
) -> None:
    """Dispatches customer anonymization consumer (GDPR)."""
    from src.modules.user.application.consumers.identity_events import (
        anonymize_customer_on_identity_deactivated,
    )

    await (
        anonymize_customer_on_identity_deactivated.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(
            identity_id=payload["identity_id"],
        )  # ty:ignore[no-matching-overload]
    )


async def _handle_role_assignment_changed(
    payload: dict, correlation_id: str | None = None
) -> None:
    """Dispatches cache invalidation for affected identity's sessions."""
    from src.modules.identity.application.consumers.role_events import (
        invalidate_permissions_cache_on_role_change,
    )

    await (
        invalidate_permissions_cache_on_role_change.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(
            identity_id=payload["identity_id"],
        )  # ty:ignore[no-matching-overload]
    )


async def _handle_linked_account_created(
    payload: dict, correlation_id: str | None = None
) -> None:
    """Dispatches customer creation for social/Telegram logins."""
    from src.modules.user.application.consumers.identity_events import (
        on_linked_account_created,
    )

    await (
        on_linked_account_created.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(
            identity_id=payload["identity_id"],
            provider=payload.get("provider", ""),
            provider_metadata=payload.get("provider_metadata", {}),
            start_param=payload.get("start_param"),
            is_new_identity=payload.get("is_new_identity", False),
            provider_sub_id=payload.get("provider_sub_id", ""),
        )  # ty:ignore[no-matching-overload]
    )


# Register IAM event mappings
register_event_handler("identity_registered", _handle_identity_registered)
register_event_handler("identity_deactivated", _handle_identity_deactivated)
register_event_handler("role_assignment_changed", _handle_role_assignment_changed)
register_event_handler("linked_account_created", _handle_linked_account_created)


# ---------------------------------------------------------------------------
# Logistics event handlers
# ---------------------------------------------------------------------------
# These currently only structured-log the event so that bookings,
# cancellations, failures and tracking updates appear in the relay's
# audit trail instead of being silently dropped under the
# "unknown event_type" branch. Wire concrete TaskIQ consumers
# (notifications, cart sync, accounting) by replacing the body with a
# `.kicker().kiq(...)` call — same pattern as the IAM handlers above.


def _logistics_event_logger(
    event_label: str,
    *,
    level: str = "info",
):
    """Build a structured-log-only handler for a logistics event_type.

    ``event_label`` is the human-readable verb (``"shipment.booked"``,
    ``"shipment.cancelled"``, …) emitted on the structured logger so
    that downstream observability tools can filter without scraping
    the Pythonic class name.
    """

    async def _handler(payload: dict, correlation_id: str | None = None) -> None:
        log = logger.bind(
            event=event_label,
            correlation_id=correlation_id,
            shipment_id=payload.get("shipment_id"),
        )
        getattr(log, level)("Outbox: logistics event observed", payload=payload)

    return _handler


register_event_handler(
    "ShipmentCreatedEvent",
    _logistics_event_logger("shipment.created"),
)
register_event_handler(
    "ShipmentBookingRequestedEvent",
    _logistics_event_logger("shipment.booking_requested"),
)
register_event_handler(
    "ShipmentBookedEvent",
    _logistics_event_logger("shipment.booked"),
)
register_event_handler(
    "ShipmentBookingFailedEvent",
    _logistics_event_logger("shipment.booking_failed", level="warning"),
)
register_event_handler(
    "ShipmentDeliveryFailedEvent",
    _logistics_event_logger("shipment.delivery_failed", level="warning"),
)
register_event_handler(
    "ShipmentCancellationRequestedEvent",
    _logistics_event_logger("shipment.cancellation_requested"),
)
register_event_handler(
    "ShipmentCancelledEvent",
    _logistics_event_logger("shipment.cancelled"),
)
register_event_handler(
    "ShipmentCancellationFailedEvent",
    _logistics_event_logger("shipment.cancellation_failed", level="warning"),
)
register_event_handler(
    "ShipmentTrackingUpdatedEvent",
    _logistics_event_logger("shipment.tracking_updated"),
)
register_event_handler(
    "ShipmentRecipientUpdatedEvent",
    _logistics_event_logger("shipment.recipient_updated"),
)
register_event_handler(
    "ShipmentDestinationUpdatedEvent",
    _logistics_event_logger("shipment.destination_updated"),
)
register_event_handler(
    "ShipmentEditTaskScheduledEvent",
    _logistics_event_logger("shipment.edit_task_scheduled"),
)
register_event_handler(
    "ShipmentEditTaskCompletedEvent",
    _logistics_event_logger("shipment.edit_task_completed"),
)
register_event_handler(
    "ShipmentEditTaskFailedEvent",
    _logistics_event_logger("shipment.edit_task_failed", level="warning"),
)
register_event_handler(
    "ShipmentIntakeScheduledEvent",
    _logistics_event_logger("shipment.intake_scheduled"),
)
register_event_handler(
    "ShipmentIntakeCancelledEvent",
    _logistics_event_logger("shipment.intake_cancelled"),
)
register_event_handler(
    "ShipmentReturnRegisteredEvent",
    _logistics_event_logger("shipment.return_registered"),
)
register_event_handler(
    "ShipmentRefusalRegisteredEvent",
    _logistics_event_logger("shipment.refusal_registered"),
)


# ---------------------------------------------------------------------------
# TaskIQ: Outbox Relay (periodic polling)
# ---------------------------------------------------------------------------


@broker.task(
    queue="outbox_relay",
    exchange="taskiq_rpc_exchange",
    routing_key="infrastructure.outbox.relay",
    max_retries=0,
    retry_on_error=False,
    timeout=55,  # 55 seconds: shorter than the cron interval (1 min)
    schedule=[{"cron": "* * * * *", "schedule_id": "outbox_relay_every_minute"}],
)
@inject
async def outbox_relay_task(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """Periodic task: fetch an outbox batch and publish events to the broker.

    Triggered by TaskIQ Scheduler (Beat) every minute.

    Args:
        session_factory: Injected async session factory.

    Returns:
        A dict with status and the number of processed events.
    """
    try:
        processed = await relay_outbox_batch(
            session_factory=session_factory,
            batch_size=100,
        )
        return {"status": "success", "processed": processed}
    except Exception:
        logger.exception("Outbox Relay: critical error in polling cycle")
        return {"status": "error", "processed": 0}


# ---------------------------------------------------------------------------
# TaskIQ: Outbox Pruning (daily cleanup)
# ---------------------------------------------------------------------------


@broker.task(
    queue="outbox_pruning",
    exchange="taskiq_rpc_exchange",
    routing_key="infrastructure.outbox.pruning",
    max_retries=1,
    retry_on_error=True,
    timeout=120,  # 2 minutes: DELETE may be heavy
    schedule=[{"cron": "0 3 * * *", "schedule_id": "outbox_pruning_daily_3am"}],
)
@inject
async def outbox_pruning_task(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """Daily task: delete processed outbox records older than 7 days.

    Triggered by TaskIQ Scheduler (Beat) daily at 03:00 UTC.

    Args:
        session_factory: Injected async session factory.

    Returns:
        A dict with status and the number of deleted records.
    """
    deleted = await prune_processed_messages(session_factory=session_factory)
    return {"status": "success", "deleted": deleted}
