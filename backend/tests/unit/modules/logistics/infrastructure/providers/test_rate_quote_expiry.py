"""
Regression tests: rate providers must stamp ``expires_at`` on every DeliveryQuote.

Without ``expires_at``, the server-side expiry check in ``CreateShipmentHandler``
is effectively dead, letting clients keep a quote (and its price) indefinitely.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.infrastructure.providers.cdek.mappers import (
    CDEK_QUOTE_TTL,
    parse_tariff_list_response,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.constants import (
    LAST_MILE_COURIER,
    LAST_MILE_PICKUP,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.rate_provider import (
    YANDEX_QUOTE_TTL,
    YandexDeliveryRateProvider,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def cdek_tariff_list_response() -> dict[str, Any]:
    return {
        "tariff_codes": [
            {
                "tariff_code": 136,
                "tariff_name": "Посылка склад-склад",
                "tariff_description": "",
                "delivery_mode": 1,
                "delivery_sum": 450.0,
                "period_min": 2,
                "period_max": 4,
                "calendar_min": 2,
                "calendar_max": 4,
            },
            {
                "tariff_code": 137,
                "tariff_name": "Посылка склад-дверь",
                "tariff_description": "",
                "delivery_mode": 2,
                "delivery_sum": 550.0,
                "period_min": 2,
                "period_max": 4,
                "calendar_min": 2,
                "calendar_max": 4,
            },
        ],
    }


def test_cdek_tarifflist_sets_expires_at(
    cdek_tariff_list_response: dict[str, Any],
) -> None:
    """CDEK quotes must carry a non-null ``expires_at`` = ``quoted_at + TTL``."""
    before = datetime.now(UTC)
    quotes = parse_tariff_list_response(cdek_tariff_list_response)
    after = datetime.now(UTC)

    assert len(quotes) == 2
    for q in quotes:
        assert q.expires_at is not None, "CDEK quote must have expires_at"
        assert q.expires_at == q.quoted_at + CDEK_QUOTE_TTL
        # Sanity: expiry falls within an expected absolute window
        assert before + CDEK_QUOTE_TTL <= q.expires_at <= after + CDEK_QUOTE_TTL


def test_cdek_quote_ttl_is_one_hour() -> None:
    assert timedelta(hours=1) == CDEK_QUOTE_TTL


@pytest.mark.asyncio
async def test_yandex_rate_provider_sets_expires_at() -> None:
    """Yandex rate provider must stamp ``expires_at`` = ``quoted_at + TTL``."""
    from src.modules.logistics.domain.value_objects import Address, Parcel, Weight

    # Fake Yandex client that returns a valid pricing-calculator body for both
    # courier and pickup tariffs.
    pricing_body = {
        "pricing_total": "225.7 RUB",
        "delivery_days": 2,
    }
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.pricing_calculator = AsyncMock(return_value=pricing_body)

    provider = YandexDeliveryRateProvider(client=client, config={})

    origin = Address(country_code="RU", city="Москва", metadata={})
    destination = Address(country_code="RU", city="Санкт-Петербург", metadata={})
    parcels = [Parcel(weight=Weight(grams=1000))]

    before = datetime.now(UTC)
    quotes = await provider.calculate_rates(origin, destination, parcels)
    after = datetime.now(UTC)

    assert len(quotes) == 2, "Expected one quote per tariff (courier + pickup)"
    service_codes = {q.rate.service_code for q in quotes}
    assert service_codes == {LAST_MILE_COURIER, LAST_MILE_PICKUP}

    for q in quotes:
        assert q.expires_at is not None, "Yandex quote must have expires_at"
        assert q.expires_at == q.quoted_at + YANDEX_QUOTE_TTL
        assert before + YANDEX_QUOTE_TTL <= q.expires_at <= after + YANDEX_QUOTE_TTL


def test_yandex_quote_ttl_is_ten_minutes() -> None:
    assert timedelta(minutes=10) == YANDEX_QUOTE_TTL
