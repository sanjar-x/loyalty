"""
CDEK tracking provider — implements ``ITrackingProvider``.

Retrieves tracking events from CDEK order info (statuses array).
"""

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    ProviderCode,
    TrackingEvent,
)
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.cdek.mappers import (
    parse_tracking_events,
)


class CdekTrackingProvider:
    """CDEK implementation of ``ITrackingProvider``.

    Tracking events are extracted from the order's ``statuses`` array
    returned by ``GET /v2/orders/{uuid}``.
    """

    def __init__(self, client: CdekClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def get_tracking(self, provider_shipment_id: str) -> list[TrackingEvent]:
        data = await self._client.get_order(provider_shipment_id)
        entity = data.get("entity", data)
        statuses = entity.get("statuses", [])
        return parse_tracking_events(statuses)
