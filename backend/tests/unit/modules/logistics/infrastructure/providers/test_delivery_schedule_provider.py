"""
Regression tests for ``CdekDeliveryScheduleProvider``:

- ``_parse_intervals`` reads ``time_intervals`` (the real CDEK key),
  not the previously-broken ``intervals``.
- ``get_estimated_intervals`` builds a body with ``tariff_code`` plus
  ``from_location`` / ``to_location``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.domain.value_objects import Address
from src.modules.logistics.infrastructure.providers.cdek.delivery_schedule_provider import (
    CdekDeliveryScheduleProvider,
    _parse_intervals,
)

pytestmark = pytest.mark.unit


def _addr(city_code: str | None = None) -> Address:
    metadata = {"cdek_city_code": city_code} if city_code else {}
    return Address(country_code="RU", city="Moscow", metadata=metadata)


class TestParseIntervals:
    def test_extracts_time_intervals_per_date(self) -> None:
        data = {
            "date_intervals": [
                {
                    "date": "2026-04-26",
                    "time_intervals": [
                        {"start_time": "09:00", "end_time": "12:00"},
                        {"start_time": "14:00", "end_time": "18:00"},
                    ],
                },
                {
                    "date": "2026-04-27",
                    "time_intervals": [
                        {"start_time": "10:00", "end_time": "13:00"},
                    ],
                },
            ]
        }

        intervals = _parse_intervals(data)

        assert len(intervals) == 3
        assert intervals[0].start_time == "09:00"
        assert intervals[0].end_time == "12:00"
        assert intervals[0].date == "2026-04-26"
        assert intervals[2].date == "2026-04-27"

    def test_skips_entries_with_old_intervals_key(self) -> None:
        # The old buggy parser keyed off ``intervals`` — make sure we
        # do NOT pick it up if a stray response shows it.
        data = {
            "date_intervals": [
                {
                    "date": "2026-04-26",
                    "intervals": [{"start_time": "09:00", "end_time": "12:00"}],
                }
            ]
        }
        assert _parse_intervals(data) == []

    def test_returns_empty_when_date_intervals_missing(self) -> None:
        assert _parse_intervals({}) == []
        assert _parse_intervals({"date_intervals": None}) == []
        assert _parse_intervals({"date_intervals": []}) == []


class TestGetEstimatedIntervals:
    @pytest.mark.asyncio
    async def test_request_body_carries_tariff_and_locations(self) -> None:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = False
        client.get_estimated_delivery_intervals.return_value = {"date_intervals": []}
        provider = CdekDeliveryScheduleProvider(client)

        await provider.get_estimated_intervals(
            origin=_addr(city_code="44"),
            destination=_addr(city_code="137"),
            tariff_code=139,
        )

        sent_body = client.get_estimated_delivery_intervals.await_args.args[0]
        assert sent_body["tariff_code"] == 139
        assert sent_body["from_location"]["code"] == 44
        assert sent_body["to_location"]["code"] == 137
