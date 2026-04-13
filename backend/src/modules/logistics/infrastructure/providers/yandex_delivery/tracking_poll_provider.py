"""
Yandex Delivery tracking poll provider — implements ``ITrackingPollProvider``.

Uses the batch POST /requests/info endpoint to poll multiple orders
in a single API call.
"""

import logging

from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    ProviderCode,
    TrackingEvent,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError
from src.modules.logistics.infrastructure.providers.yandex_delivery.client import (
    YandexDeliveryClient,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.mappers import (
    parse_batch_requests_info,
)

logger = logging.getLogger(__name__)

# Yandex API may limit batch size; chunk to avoid issues
_MAX_BATCH_SIZE = 100


class YandexDeliveryTrackingPollProvider:
    """Yandex Delivery implementation of ``ITrackingPollProvider``.

    Uses the batch ``POST /requests/info`` endpoint which accepts
    multiple request_ids in a single call — more efficient than
    polling each shipment individually.
    """

    def __init__(self, client: YandexDeliveryClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_YANDEX_DELIVERY

    async def poll_tracking_batch(
        self, provider_shipment_ids: list[str]
    ) -> dict[str, list[TrackingEvent]]:
        result: dict[str, list[TrackingEvent]] = {}

        async with self._client:
            for i in range(0, len(provider_shipment_ids), _MAX_BATCH_SIZE):
                chunk = provider_shipment_ids[i : i + _MAX_BATCH_SIZE]
                try:
                    data = await self._client.get_requests_info(chunk)
                    parsed = parse_batch_requests_info(data)
                    result.update(parsed)
                except ProviderHTTPError:
                    logger.exception(
                        "Failed to poll Yandex tracking batch (chunk %d–%d)",
                        i,
                        i + len(chunk),
                    )
                    for sid in chunk:
                        result.setdefault(sid, [])

        # Ensure all requested IDs are in the result
        for sid in provider_shipment_ids:
            result.setdefault(sid, [])

        return result
