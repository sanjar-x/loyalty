"""
Webhook receiver router for logistics provider callbacks.

Unified entry point — the ``{provider_code}`` path parameter
determines which provider adapter parses the payload.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, status

from src.modules.logistics.domain.interfaces import (
    IShippingProviderRegistry,
)
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
    events = await adapter.parse_events(body=raw_body)

    logger.info(
        "Webhook processed",
        provider=provider_code,
        event_count=len(events),
    )

    return {
        "status": "processed",
        "provider": provider_code,
        "event_count": len(events),
    }
