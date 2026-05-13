"""
Regression tests for ``YandexDeliveryDeliveryScheduleProvider``:

- ``get_estimated_intervals`` builds an /offers/info request from the
  passed source/destination, picks the right ``last_mile_policy`` from
  ``tariff_code``, and parses the UTC windows into DeliveryInterval.
- ``get_intervals`` delegates to /request/datetime_options for an
  already-booked shipment.
- HTTP 400 (Yandex's "no_delivery_options") is translated into an
  empty list rather than an exception.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.domain.value_objects import Address
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError
from src.modules.logistics.infrastructure.providers.yandex_delivery.constants import (
    LAST_MILE_COURIER,
    LAST_MILE_PICKUP,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.delivery_schedule_provider import (
    YandexDeliveryDeliveryScheduleProvider,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.mappers import (
    parse_datetime_options,
    parse_offer_info_intervals,
)

pytestmark = pytest.mark.unit


def _addr(platform_id: str | None = None, raw: str | None = None) -> Address:
    metadata = {"platform_station_id": platform_id} if platform_id else {}
    return Address(country_code="RU", city="Moscow", raw_address=raw, metadata=metadata)


@pytest.fixture
def yandex_client() -> AsyncMock:
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


class TestParseOfferInfoIntervals:
    def test_collapses_utc_window_to_date_and_hours(self) -> None:
        data = {
            "offers": [
                {
                    "from": "2026-01-18T07:00:00.000000Z",
                    "to": "2026-01-18T15:00:00.000000Z",
                },
                {
                    "from": "2026-01-19T09:00:00.000000Z",
                    "to": "2026-01-19T13:00:00.000000Z",
                },
            ]
        }

        intervals = parse_offer_info_intervals(data)

        assert [(i.date, i.start_time, i.end_time) for i in intervals] == [
            ("2026-01-18", "07:00", "15:00"),
            ("2026-01-19", "09:00", "13:00"),
        ]

    def test_supports_unix_timestamps(self) -> None:
        # 2026-01-18T00:00:00Z = 1768694400; +6h = 1768716000
        data = {"offers": [{"from": 1768694400, "to": 1768716000}]}

        intervals = parse_offer_info_intervals(data)

        assert len(intervals) == 1
        assert intervals[0].date == "2026-01-18"
        assert intervals[0].start_time == "00:00"
        assert intervals[0].end_time == "06:00"

    def test_skips_entries_with_unparseable_bounds(self) -> None:
        data = {
            "offers": [
                {"from": "not a date", "to": "2026-01-18T07:00:00Z"},
                {"from": "2026-01-18T07:00:00Z"},  # missing 'to'
            ]
        }
        assert parse_offer_info_intervals(data) == []


class TestParseDatetimeOptions:
    def test_options_match_offers_shape(self) -> None:
        data = {
            "options": [
                {
                    "from": "2026-01-20T10:00:00.000000Z",
                    "to": "2026-01-20T14:00:00.000000Z",
                }
            ]
        }
        intervals = parse_datetime_options(data)
        assert len(intervals) == 1
        assert intervals[0].date == "2026-01-20"


class TestGetEstimatedIntervals:
    @pytest.mark.asyncio
    async def test_courier_tariff_picks_time_interval(
        self, yandex_client: AsyncMock
    ) -> None:
        yandex_client.offers_info.return_value = {
            "offers": [
                {
                    "from": "2026-01-18T07:00:00Z",
                    "to": "2026-01-18T15:00:00Z",
                }
            ]
        }
        provider = YandexDeliveryDeliveryScheduleProvider(
            yandex_client, {"platform_station_id": "src-uuid"}
        )

        intervals = await provider.get_estimated_intervals(
            origin=_addr(platform_id="src-uuid"),
            destination=_addr(raw="Moscow, Lenina, 1"),
            tariff_code=1,
        )

        assert len(intervals) == 1
        last_mile = yandex_client.offers_info.await_args.kwargs["last_mile_policy"]
        assert last_mile == LAST_MILE_COURIER
        body = yandex_client.offers_info.await_args.args[0]
        assert body["source"] == {"platform_station_id": "src-uuid"}
        assert body["destination"]["address"] == "Moscow, Lenina, 1"

    @pytest.mark.asyncio
    async def test_pickup_tariff_picks_self_pickup(
        self, yandex_client: AsyncMock
    ) -> None:
        yandex_client.offers_info.return_value = {"offers": []}
        provider = YandexDeliveryDeliveryScheduleProvider(
            yandex_client, {"platform_station_id": "src-uuid"}
        )

        await provider.get_estimated_intervals(
            origin=_addr(platform_id="src-uuid"),
            destination=_addr(platform_id="dst-uuid"),
            tariff_code=2,
        )

        assert (
            yandex_client.offers_info.await_args.kwargs["last_mile_policy"]
            == LAST_MILE_PICKUP
        )

    @pytest.mark.asyncio
    async def test_no_delivery_options_returns_empty_list(
        self, yandex_client: AsyncMock
    ) -> None:
        yandex_client.offers_info.side_effect = ProviderHTTPError(
            status_code=400,
            message="No delivery options for interval",
        )
        provider = YandexDeliveryDeliveryScheduleProvider(
            yandex_client, {"platform_station_id": "src-uuid"}
        )

        intervals = await provider.get_estimated_intervals(
            origin=_addr(platform_id="src-uuid"),
            destination=_addr(raw="Moscow, Lenina, 1"),
            tariff_code=1,
        )

        assert intervals == []

    @pytest.mark.asyncio
    async def test_5xx_propagates(self, yandex_client: AsyncMock) -> None:
        yandex_client.offers_info.side_effect = ProviderHTTPError(
            status_code=500, message="boom"
        )
        provider = YandexDeliveryDeliveryScheduleProvider(yandex_client, {})

        with pytest.raises(ProviderHTTPError):
            await provider.get_estimated_intervals(
                origin=_addr(platform_id="src-uuid"),
                destination=_addr(raw="Moscow, Lenina, 1"),
                tariff_code=1,
            )


class TestGetIntervals:
    @pytest.mark.asyncio
    async def test_delegates_to_datetime_options(
        self, yandex_client: AsyncMock
    ) -> None:
        yandex_client.request_datetime_options.return_value = {
            "options": [
                {
                    "from": "2026-01-25T08:00:00Z",
                    "to": "2026-01-25T20:00:00Z",
                }
            ]
        }
        provider = YandexDeliveryDeliveryScheduleProvider(yandex_client, {})

        intervals = await provider.get_intervals("request-uuid")

        yandex_client.request_datetime_options.assert_awaited_once_with("request-uuid")
        assert len(intervals) == 1
        assert intervals[0].date == "2026-01-25"
        assert intervals[0].start_time == "08:00"
        assert intervals[0].end_time == "20:00"

    @pytest.mark.asyncio
    async def test_400_returns_empty(self, yandex_client: AsyncMock) -> None:
        yandex_client.request_datetime_options.side_effect = ProviderHTTPError(
            status_code=400, message="No delivery options"
        )
        provider = YandexDeliveryDeliveryScheduleProvider(yandex_client, {})
        assert await provider.get_intervals("request-uuid") == []
