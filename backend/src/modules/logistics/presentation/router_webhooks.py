"""
Webhook receiver router for logistics provider callbacks.

Unified entry point — the ``{provider_code}`` path parameter
determines which provider adapter parses the payload.
"""

from fastapi import APIRouter, Request, status

webhook_router = APIRouter(
    prefix="/logistics/webhooks",
    tags=["Logistics Webhooks"],
)


@webhook_router.post(
    path="/{provider_code}",
    status_code=status.HTTP_200_OK,
    summary="Receive provider webhook",
)
async def receive_webhook(
    provider_code: str,
    request: Request,
) -> dict:
    """Unified webhook receiver.

    Provider-specific adapters (not yet implemented) will:
    1. Validate the webhook signature
    2. Parse the provider-specific payload
    3. Map to TrackingEvent(s)
    4. Call IngestTrackingHandler

    This base implementation acknowledges the webhook to prevent
    retries while provider adapters are not yet registered.
    """
    body = await request.body()
    # TODO: dispatch to provider-specific webhook adapter via registry
    return {"status": "acknowledged", "provider": provider_code, "bytes": len(body)}
