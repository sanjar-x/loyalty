"""
Yandex Delivery tracking provider — implements ``ITrackingProvider``.

Retrieves tracking events from GET /request/history.
"""

from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    ProviderCode,
    TrackingEvent,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.client import (
    YandexDeliveryClient,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.mappers import (
    parse_tracking_history,
)


class YandexDeliveryTrackingProvider:
    """Yandex Delivery implementation of ``ITrackingProvider``.

    Tracking events are extracted from the ``state_history`` array
    returned by ``GET /request/history``.
    """

    def __init__(self, client: YandexDeliveryClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_YANDEX_DELIVERY

    async def get_tracking(self, provider_shipment_id: str) -> list[TrackingEvent]:
        async with self._client:
            data = await self._client.get_request_history(provider_shipment_id)
        return parse_tracking_history(data)
