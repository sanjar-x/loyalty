"""
Webhook receiver router for logistics provider callbacks.

Unified entry point — the ``{provider_code}`` path parameter
determines which provider adapter parses the payload.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, status

from src.modules.logistics.application.commands.ingest_tracking import (
    IngestTrackingCommand,
    IngestTrackingHandler,
)
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import (
    IShippingProviderRegistry,
)
from src.shared.exceptions import UnauthorizedError
from src.shared.interfaces.logger import ILogger

webhook_router = APIRouter(
    prefix="/logistics/webhooks",
    tags=["Logistics Webhooks"],
    route_class=DishkaRoute,
)


@webhook_router.post(
    path="/{provider_code}",
    status_code=status.HTTP_200_OK,
    summary="Receive provider webhook",
)
async def receive_webhook(
    provider_code: str,
    request: Request,
    registry: FromDishka[IShippingProviderRegistry],
    ingest_handler: FromDishka[IngestTrackingHandler],
    logger: FromDishka[ILogger],
) -> dict:
    """Unified webhook receiver.

    Dispatches to the registered IWebhookAdapter for the provider.
    The adapter validates signature, parses payload, and returns
    normalized tracking events for ingestion.
    """
    if not registry.has_webhook_adapter(provider_code):
        logger.warning(
            "Webhook received for unregistered provider",
            provider=provider_code,
        )
        return {"status": "ignored", "provider": provider_code}

    raw_body = await request.body()

    adapter = registry.get_webhook_adapter(provider_code)

    # Validate signature BEFORE parsing to reject forged payloads
    headers_dict = dict(request.headers)
    is_valid = await adapter.validate_signature(headers=headers_dict, body=raw_body)
    if not is_valid:
        logger.warning(
            "Invalid webhook signature",
            provider=provider_code,
        )
        raise UnauthorizedError(
            message=f"Invalid webhook signature for provider '{provider_code}'",
        )

    parsed = await adapter.parse_events(body=raw_body)

    if not parsed:
        # Adapter recognised the payload but yielded no tracking events
        # (e.g. CDEK PRINT_FORM, DOWNLOAD_PHOTO, PREALERT_CLOSED). Log
        # for audit so non-tracking events aren't silently dropped —
        # a future consumer can persist them to a dedicated
        # ``provider_webhook_log`` table without touching this router.
        logger.info(
            "Webhook accepted but produced no tracking events",
            provider=provider_code,
            raw_body_size=len(raw_body),
        )
        return {
            "status": "accepted_no_tracking",
            "provider": provider_code,
        }

    total_new = 0
    skipped_unknown = 0
    failed = 0
    for provider_shipment_id, events in parsed:
        if not events:
            continue
        try:
            result = await ingest_handler.handle(
                IngestTrackingCommand(
                    provider_code=provider_code,
                    provider_shipment_id=provider_shipment_id,
                    events=events,
                    raw_payload=raw_body.decode("utf-8", errors="replace"),
                )
            )
            total_new += result.new_events_count
        except ShipmentNotFoundError:
            # Webhook references a shipment we don't track — common
            # when the carrier delivers events for another tenant or
            # test environment sharing the same secret. Returning
            # 4xx invites a poison-pill retry loop; ack and continue.
            skipped_unknown += 1
            logger.warning(
                "Webhook references unknown shipment; acknowledging",
                provider=provider_code,
                provider_shipment_id=provider_shipment_id,
            )
        except Exception:
            # Any other per-shipment failure (optimistic-lock
            # ConflictError, validation, transient DB issue, parser
            # bug) must not poison the rest of the batch. Carriers
            # do not honour partial 4xx — they re-deliver the entire
            # payload, re-applying events for shipments we already
            # processed. The periodic ITrackingPollProvider task
            # will backfill anything we drop here on the next run.
            failed += 1
            logger.exception(
                "Webhook ingest failed for shipment; acknowledging "
                "to avoid carrier retry storm",
                provider=provider_code,
                provider_shipment_id=provider_shipment_id,
            )

    logger.info(
        "Webhook processed",
        provider=provider_code,
        shipment_count=len(parsed),
        new_events=total_new,
        skipped_unknown=skipped_unknown,
        failed=failed,
    )

    return {
        "status": "processed",
        "provider": provider_code,
    }
