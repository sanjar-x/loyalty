"""
CDEK pickup point provider — implements ``IPickupPointProvider``.

Lists CDEK delivery points (PVZ / postamats) from the
``GET /v2/deliverypoints`` endpoint with automatic pagination.
"""

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    PickupPoint,
    PickupPointQuery,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.cdek.mappers import (
    build_delivery_points_params,
    parse_delivery_points,
)


class CdekPickupPointProvider:
    """CDEK implementation of ``IPickupPointProvider``.

    Automatically paginates through CDEK's delivery points API
    to return all matching points for the query.
    """

    def __init__(self, client: CdekClient) -> None:
        self._client: CdekClient = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def list_pickup_points(self, query: PickupPointQuery) -> list[PickupPoint]:
        params = build_delivery_points_params(query)
        async with self._client:
            raw = await self._client.list_all_delivery_points(params)
        return parse_delivery_points(raw)
