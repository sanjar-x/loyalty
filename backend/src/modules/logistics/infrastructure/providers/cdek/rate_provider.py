"""
CDEK rate provider — implements ``IRateProvider``.

Calls CDEK calculator tarifflist endpoint and maps results
to domain ``DeliveryQuote`` objects.
"""

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    Address,
    DeliveryQuote,
    Parcel,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.cdek.mappers import (
    build_calculator_request,
    parse_tariff_list_response,
)


class CdekRateProvider:
    """CDEK implementation of ``IRateProvider``."""

    def __init__(self, client: CdekClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def calculate_rates(
        self,
        origin: Address,
        destination: Address,
        parcels: list[Parcel],
    ) -> list[DeliveryQuote]:
        body = build_calculator_request(origin, destination, parcels)
        async with self._client:
            data = await self._client.calculate_tariff_list(body)
        return parse_tariff_list_response(data)
