"""
Yandex Delivery pickup point provider — implements ``IPickupPointProvider``.

Lists pickup and drop-off points via POST /pickup-points/list.
"""

from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    PickupPoint,
    PickupPointQuery,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.client import (
    YandexDeliveryClient,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.mappers import (
    build_pickup_points_request,
    parse_pickup_points,
)


class YandexDeliveryPickupPointProvider:
    """Yandex Delivery implementation of ``IPickupPointProvider``."""

    def __init__(self, client: YandexDeliveryClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_YANDEX_DELIVERY

    async def list_pickup_points(self, query: PickupPointQuery) -> list[PickupPoint]:
        body = build_pickup_points_request(query)
        async with self._client:
            data = await self._client.list_pickup_points(body)
        return parse_pickup_points(data)
