"""
Regression tests for ``YandexDeliveryDeliveryScheduleProvider.get_actual_delivery_info``:

- Parses ``GET /request/actual_info`` (3.05) into ActualDeliveryInfo.
- HTTP 400 / 404 from the provider → ``None`` (not yet committed).
- Other HTTP errors propagate.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError
from src.modules.logistics.infrastructure.providers.yandex_delivery.delivery_schedule_provider import (
    YandexDeliveryDeliveryScheduleProvider,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def yandex_client() -> AsyncMock:
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


class TestActualDeliveryInfo:
    @pytest.mark.asyncio
    async def test_parses_local_time_with_tz_suffix(
        self, yandex_client: AsyncMock
    ) -> None:
        yandex_client.get_actual_info.return_value = {
            "delivery_date": "2026-04-30",
            "delivery_interval": {
                "from": "10:00+03:00",
                "to": "23:00+03:00",
            },
        }
        provider = YandexDeliveryDeliveryScheduleProvider(yandex_client, {})

        info = await provider.get_actual_delivery_info("request-uuid")

        assert info is not None
        assert info.delivery_date == "2026-04-30"
        assert info.interval_start == "10:00"
        assert info.interval_end == "23:00"
        assert info.timezone_offset == "+03:00"

    @pytest.mark.asyncio
    async def test_negative_tz_offset(self, yandex_client: AsyncMock) -> None:
        yandex_client.get_actual_info.return_value = {
            "delivery_date": "2026-04-30",
            "delivery_interval": {
                "from": "08:00-05:00",
                "to": "20:00-05:00",
            },
        }
        provider = YandexDeliveryDeliveryScheduleProvider(yandex_client, {})

        info = await provider.get_actual_delivery_info("request-uuid")

        assert info is not None
        assert info.timezone_offset == "-05:00"

    @pytest.mark.asyncio
    async def test_400_returns_none(self, yandex_client: AsyncMock) -> None:
        yandex_client.get_actual_info.side_effect = ProviderHTTPError(
            status_code=400, message="not yet"
        )
        provider = YandexDeliveryDeliveryScheduleProvider(yandex_client, {})

        assert await provider.get_actual_delivery_info("request-uuid") is None

    @pytest.mark.asyncio
    async def test_404_returns_none(self, yandex_client: AsyncMock) -> None:
        yandex_client.get_actual_info.side_effect = ProviderHTTPError(
            status_code=404, message="not found"
        )
        provider = YandexDeliveryDeliveryScheduleProvider(yandex_client, {})

        assert await provider.get_actual_delivery_info("request-uuid") is None

    @pytest.mark.asyncio
    async def test_500_propagates(self, yandex_client: AsyncMock) -> None:
        yandex_client.get_actual_info.side_effect = ProviderHTTPError(
            status_code=500, message="boom"
        )
        provider = YandexDeliveryDeliveryScheduleProvider(yandex_client, {})

        with pytest.raises(ProviderHTTPError):
            await provider.get_actual_delivery_info("request-uuid")

    @pytest.mark.asyncio
    async def test_partial_payload_returns_none(self, yandex_client: AsyncMock) -> None:
        # Missing delivery_interval
        yandex_client.get_actual_info.return_value = {"delivery_date": "2026-04-30"}
        provider = YandexDeliveryDeliveryScheduleProvider(yandex_client, {})

        assert await provider.get_actual_delivery_info("request-uuid") is None
