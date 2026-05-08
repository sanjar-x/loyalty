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
            identity_id=payload.get("identity_id"),
            email=payload.get("email", ""),
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
            identity_id=payload.get("identity_id"),
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
            identity_id=payload.get("identity_id"),
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
            identity_id=payload.get("identity_id"),
            provider=payload.get("provider", ""),
            provider_metadata=payload.get("provider_metadata", {}),
            start_param=payload.get("start_param"),
            is_new_identity=payload.get("is_new_identity", False),
            provider_sub_id=payload.get("provider_sub_id", ""),
        )  # ty:ignore[no-matching-overload]
    )


# Register IAM event mappings.
#
# REFACT-001 PR-4 dual-registration: each handler is registered against
# both the legacy snake_case ``event_type`` (events emitted by the
# pre-PR-4 codebase still sitting in the outbox or in a slow consumer
# path) AND the canonical PascalCase ``event_type`` introduced by the
# events.py migration. Removed in REFACT-008 (7 days post-merge) once
# the snake_case shims age out -- both sides MUST resolve to the same
# handler so dispatch is event-name-agnostic.
#
# Handler bodies are legacy-payload-tolerant: ``payload.get(field, default)``
# everywhere, so a snake_case-emitted payload missing newer fields still
# routes correctly without TypeError.
register_event_handler("identity_registered", _handle_identity_registered)
register_event_handler("IdentityRegisteredEvent", _handle_identity_registered)
register_event_handler("identity_deactivated", _handle_identity_deactivated)
register_event_handler("IdentityDeactivatedEvent", _handle_identity_deactivated)
register_event_handler("role_assignment_changed", _handle_role_assignment_changed)
register_event_handler("RoleAssignmentChangedEvent", _handle_role_assignment_changed)
register_event_handler("linked_account_created", _handle_linked_account_created)
register_event_handler("LinkedAccountCreatedEvent", _handle_linked_account_created)


# ---------------------------------------------------------------------------
# Supplier event handlers (REFACT-001 PR-4)
# ---------------------------------------------------------------------------
#
# Supplier currently has no downstream consumers wired to these events --
# the handler below structured-logs the payload so the relay observes a
# known event_type rather than the «unknown event_type, skipping» branch.
# Dual-registration covers both legacy dotted-snake (``supplier.created``)
# and canonical PascalCase (``SupplierCreatedEvent``); REFACT-008 drops
# the snake-case shims 7 days after PR-4 merge.
#
# Handler is payload-tolerant: derives ``supplier_id`` from
# ``payload.get("supplier_id")`` (canonical) with fallback to
# ``payload.get("aggregate_id")`` (legacy emitter, supplier_id absent).


def _structured_log_handler(
    event_label: str,
    *,
    bind_fields: tuple[str, ...] = (),
    level: str = "info",
):
    """Build a structured-log-only outbox handler (REC-034).

    Returns a coroutine suitable for ``register_event_handler`` that
    binds ``event_label`` plus any payload fields named in
    ``bind_fields`` to the structured logger and emits the configured
    ``level`` line. Replaces three near-identical factories
    (``_logistics_event_logger``, ``_favorites_event_logger``,
    ``_handle_supplier_event``) that differed only in which fields
    they extracted from the payload.
    """

    async def _handler(payload: dict, correlation_id: str | None = None) -> None:
        bound: dict[str, object] = {
            "event": event_label,
            "correlation_id": correlation_id,
        }
        for field in bind_fields:
            bound[field] = payload.get(field)
        log = logger.bind(**bound)
        getattr(log, level)("Outbox: event observed", payload=payload)

    return _handler


_supplier_handler = _structured_log_handler(
    "supplier.event", bind_fields=("supplier_id", "aggregate_id", "event_type")
)


register_event_handler("supplier.created", _supplier_handler)
register_event_handler("SupplierCreatedEvent", _supplier_handler)
register_event_handler("supplier.updated", _supplier_handler)
register_event_handler("SupplierUpdatedEvent", _supplier_handler)
register_event_handler("supplier.deactivated", _supplier_handler)
register_event_handler("SupplierDeactivatedEvent", _supplier_handler)
register_event_handler("supplier.activated", _supplier_handler)
register_event_handler("SupplierActivatedEvent", _supplier_handler)


# ---------------------------------------------------------------------------
# Logistics event handlers
# ---------------------------------------------------------------------------
# These currently only structured-log the event so that bookings,
# cancellations, failures and tracking updates appear in the relay's
# audit trail instead of being silently dropped under the
# "unknown event_type" branch. Wire concrete TaskIQ consumers
# (notifications, cart sync, accounting) by replacing the body with a
# `.kicker().kiq(...)` call — same pattern as the IAM handlers above.


def _logistics_event_logger(event_label: str, *, level: str = "info"):
    """Logistics-flavoured wrapper around :func:`_structured_log_handler`."""
    return _structured_log_handler(
        event_label, bind_fields=("shipment_id",), level=level
    )


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
# Favorites event handlers
# ---------------------------------------------------------------------------
# Structured-log-only for now: favorites events are useful as analytics
# / co-view signals (a strong "interest" indicator for the activity
# module), but no synchronous downstream consumer exists yet. Replace
# the body with a `.kicker().kiq(...)` call when wiring the activity
# enrichment task — same pattern as the IAM handlers above.


def _favorites_event_logger(event_label: str):
    """Favorites-flavoured wrapper around :func:`_structured_log_handler`."""
    return _structured_log_handler(event_label, bind_fields=("list_id", "identity_id"))


register_event_handler(
    "FavoriteListCreatedEvent",
    _favorites_event_logger("favorites.list_created"),
)
register_event_handler(
    "FavoriteListRenamedEvent",
    _favorites_event_logger("favorites.list_renamed"),
)
register_event_handler(
    "FavoriteListDeletedEvent",
    _favorites_event_logger("favorites.list_deleted"),
)
register_event_handler(
    "FavoriteItemAddedEvent",
    _favorites_event_logger("favorites.item_added"),
)
register_event_handler(
    "FavoriteItemRemovedEvent",
    _favorites_event_logger("favorites.item_removed"),
)


# ---------------------------------------------------------------------------
# Catalog SKU pricing → admin SSE bridge (CAT-005)
# ---------------------------------------------------------------------------


async def _handle_sku_priced(payload: dict, correlation_id: str | None = None) -> None:
    """Bridge ``SKUPricedEvent`` → per-product Redis pub/sub channel.

    Schema-validates the payload before kicking the SSE consumer: a
    ``priced`` event MUST carry ``selling_price_amount`` /
    ``selling_currency`` / ``product_id`` / ``sku_id``. Missing fields
    indicate an event-schema regression, NOT a transient broker fault —
    publishing a partial frame would surface as
    ``pricingStatus="priced"`` + ``sellingPrice=null`` in the admin UI,
    confusing operators worse than a missing notification.

    Broker-enqueue failures (``kiq()`` raises) propagate so the outbox
    relay marks the row failed and retries on the next poll cycle —
    SKU is already priced in DB, only the SSE notification is missed.
    """
    from src.modules.catalog.application.consumers.sku_pricing_events import (
        publish_sku_pricing_status,
    )

    product_id = payload.get("product_id")
    sku_id = payload.get("sku_id")
    selling_price_amount = payload.get("selling_price_amount")
    selling_currency = payload.get("selling_currency")
    if (
        product_id is None
        or sku_id is None
        or selling_price_amount is None
        or selling_currency is None
    ):
        logger.error(
            "sku_priced_event_malformed_skipped",
            product_id=product_id,
            sku_id=sku_id,
            selling_price_amount=selling_price_amount,
            selling_currency=selling_currency,
            correlation_id=correlation_id,
        )
        return

    priced_at = payload.get("occurred_at") or payload.get("priced_at")
    try:
        await (
            publish_sku_pricing_status.kicker()
            .with_labels(**_build_labels(correlation_id))
            .kiq(
                product_id=str(product_id),
                sku_id=str(sku_id),
                pricing_status="priced",
                selling_price_amount=selling_price_amount,
                selling_currency=selling_currency,
                priced_at=priced_at,
                priced_failure_reason=None,
            )  # ty:ignore[no-matching-overload]
        )
    except Exception:
        # Broker enqueue failed — SKU is priced in DB and storefront
        # already serves the right price, only admin SSE will not fire.
        # Log the FULL payload so ops can replay manually if relay
        # retries also exhaust. Re-raise so the relay marks this event
        # failed and re-tries it on the next poll.
        logger.exception(
            "sku_priced_sse_bridge_dispatch_failed",
            payload=payload,
            correlation_id=correlation_id,
        )
        raise


async def _handle_sku_pricing_failed(
    payload: dict, correlation_id: str | None = None
) -> None:
    """Bridge ``SKUPricingFailedEvent`` → per-product Redis pub/sub channel.

    Validates required fields (``product_id``, ``sku_id``,
    ``failure_reason``) before kicking — a ``failed`` frame without a
    reason field is worse than no notification: the UI shows a
    permanent "FAILED" badge with no diagnosis.

    Broker-enqueue failures propagate (same contract as
    :func:`_handle_sku_priced`).
    """
    from src.modules.catalog.application.consumers.sku_pricing_events import (
        publish_sku_pricing_status,
    )

    product_id = payload.get("product_id")
    sku_id = payload.get("sku_id")
    failure_reason = payload.get("failure_reason")
    if product_id is None or sku_id is None or failure_reason is None:
        logger.error(
            "sku_pricing_failed_event_malformed_skipped",
            product_id=product_id,
            sku_id=sku_id,
            failure_reason=failure_reason,
            correlation_id=correlation_id,
        )
        return

    try:
        await (
            publish_sku_pricing_status.kicker()
            .with_labels(**_build_labels(correlation_id))
            .kiq(
                product_id=str(product_id),
                sku_id=str(sku_id),
                pricing_status=payload.get("pricing_status", "formula_error"),
                selling_price_amount=None,
                selling_currency=None,
                priced_at=payload.get("occurred_at"),
                priced_failure_reason=failure_reason,
            )  # ty:ignore[no-matching-overload]
        )
    except Exception:
        logger.exception(
            "sku_pricing_failed_sse_bridge_dispatch_failed",
            payload=payload,
            correlation_id=correlation_id,
        )
        raise


register_event_handler("SKUPricedEvent", _handle_sku_priced)
register_event_handler("SKUPricingFailedEvent", _handle_sku_pricing_failed)


# ---------------------------------------------------------------------------
# Image → catalog sync bridge (IMG-004)
# ---------------------------------------------------------------------------


async def _handle_storage_object_processed(
    payload: dict, correlation_id: str | None = None
) -> None:
    """Bridge ``StorageObjectProcessedEvent`` → catalog media-sync consumer.

    Catalog mirrors ``url`` / ``image_variants`` into denormalised
    ``media_assets`` rows so the storefront doesn't need a cross-module
    JOIN. After ``/reupload`` triggers a fresh worker pass the URL
    changes — the consumer re-syncs every catalog row pointing at this
    ``storage_object_id`` so the denorm stays consistent.
    """
    from src.modules.catalog.application.consumers.storage_object_processed import (
        sync_media_assets_on_processed,
    )

    storage_object_id = payload.get("storage_object_id")
    url = payload.get("url")
    if storage_object_id is None or url is None:
        logger.error(
            "storage_object_processed_event_malformed_skipped",
            storage_object_id=storage_object_id,
            url=url,
            correlation_id=correlation_id,
        )
        return

    try:
        await (
            sync_media_assets_on_processed.kicker()
            .with_labels(**_build_labels(correlation_id))
            .kiq(
                storage_object_id=str(storage_object_id),
                url=str(url),
                image_variants=payload.get("image_variants") or [],
            )  # ty:ignore[no-matching-overload]
        )
    except Exception:
        logger.exception(
            "storage_object_processed_bridge_dispatch_failed",
            payload=payload,
            correlation_id=correlation_id,
        )
        raise


register_event_handler("StorageObjectProcessedEvent", _handle_storage_object_processed)


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
        # Re-raise after logging so TaskIQ surfaces this in
        # ``failed_tasks`` instead of returning a synthetic
        # ``{"status": "error"}`` that monitoring tools never see.
        # With ``max_retries=0, retry_on_error=False`` the failure
        # lands in the DLQ immediately — exactly the signal HARD-2
        # alerting watches for. Per-event isolation already happens
        # inside ``relay_outbox_batch`` (each event in its own
        # transaction), so a re-raise here only fires on
        # batch-level catastrophes (DB unreachable, session-factory
        # broken, …) which absolutely should page someone.
        logger.exception("Outbox Relay: critical error in polling cycle")
        raise


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
