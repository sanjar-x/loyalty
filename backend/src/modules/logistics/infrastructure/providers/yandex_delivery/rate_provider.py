"""
Yandex Delivery rate provider — implements ``IRateProvider``.

Uses the pricing-calculator endpoint for preliminary cost estimation.
Calls twice (courier + pickup) to return both delivery options.
"""

import logging
from typing import Any

from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    Address,
    DeliveryQuote,
    Parcel,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError
from src.modules.logistics.infrastructure.providers.yandex_delivery.client import (
    YandexDeliveryClient,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.constants import (
    LAST_MILE_COURIER,
    LAST_MILE_PICKUP,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.mappers import (
    build_pricing_request,
    parse_pricing_response,
)

logger = logging.getLogger(__name__)


class YandexDeliveryRateProvider:
    """Yandex Delivery implementation of ``IRateProvider``.

    Calls the pricing-calculator endpoint for each delivery type
    (courier and pickup) and returns the available quotes.
    """

    def __init__(self, client: YandexDeliveryClient, config: dict[str, Any]) -> None:
        self._client = client
        self._config = config

    def provider_code(self) -> ProviderCode:
        return PROVIDER_YANDEX_DELIVERY

    async def calculate_rates(
        self,
        origin: Address,
        destination: Address,
        parcels: list[Parcel],
    ) -> list[DeliveryQuote]:
        quotes: list[DeliveryQuote] = []

        for tariff in (LAST_MILE_COURIER, LAST_MILE_PICKUP):
            body = build_pricing_request(
                origin, destination, parcels, tariff, self._config
            )
            try:
                async with self._client:
                    data = await self._client.pricing_calculator(body)
            except ProviderHTTPError as exc:
                if exc.status_code == 400:
                    logger.debug(
                        "No Yandex rates for tariff %s: %s", tariff, exc.message
                    )
                    continue
                raise

            rate = parse_pricing_response(data, tariff)
            if rate is None:
                continue

            import uuid
            from datetime import UTC, datetime

            quotes.append(
                DeliveryQuote(
                    id=uuid.uuid4(),
                    rate=rate,
                    provider_payload="{}",
                    quoted_at=datetime.now(UTC),
                )
            )

        return quotes
