"""
CDEK webhook adapter — implements ``IWebhookAdapter``.

Parses inbound CDEK ORDER_STATUS webhooks into domain TrackingEvents.

CDEK does not use HMAC-based signature verification for webhooks.
Authentication is based on the webhook URL being registered with CDEK
and the webhook containing the correct ``uuid`` that matches a known order.
"""

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    ProviderCode,
    TrackingEvent,
)
from src.modules.logistics.infrastructure.providers.cdek.mappers import (
    parse_webhook_body,
)


class CdekWebhookAdapter:
    """CDEK implementation of ``IWebhookAdapter``.

    CDEK webhooks are verified by URL registration (no HMAC signature).
    ``validate_signature`` always returns True — security relies on
    the webhook URL being secret and registered only via the CDEK API.
    """

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def validate_signature(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> bool:
        # CDEK does not sign webhook payloads.
        # Verification is based on URL secrecy + order UUID matching.
        return True

    async def parse_events(
        self,
        body: bytes,
    ) -> list[tuple[str, list[TrackingEvent]]]:
        return parse_webhook_body(body)
