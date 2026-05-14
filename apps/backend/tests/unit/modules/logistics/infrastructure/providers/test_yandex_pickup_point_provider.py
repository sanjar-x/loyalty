"""
Regression tests for ``YandexDeliveryPickupPointProvider``:

A bare ``city`` is not a valid ``/pickup-points/list`` filter — the
provider resolves it to a numeric ``geo_id`` via ``location/detect``
(2.01) before listing, so a city-level query stays bounded instead of
pulling the entire catalogue. A query that already carries a lat/lng
box skips the extra round-trip; resolved ids are memoised in a bounded
LRU.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.domain.value_objects import PickupPointQuery
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError
from src.modules.logistics.infrastructure.providers.yandex_delivery.pickup_point_provider import (
    YandexDeliveryPickupPointProvider,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def yandex_client() -> AsyncMock:
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    client.list_pickup_points.return_value = {"points": []}
    return client


class TestGeoIdResolution:
    @pytest.mark.asyncio
    async def test_city_query_resolves_geo_id_then_lists(
        self, yandex_client: AsyncMock
    ) -> None:
        yandex_client.detect_location.return_value = {
            "variants": [{"geo_id": 213, "address": "Москва"}]
        }
        provider = YandexDeliveryPickupPointProvider(yandex_client)

        await provider.list_pickup_points(PickupPointQuery(city="Москва"))

        yandex_client.detect_location.assert_awaited_once_with("Москва")
        body = yandex_client.list_pickup_points.await_args.args[0]
        assert body["geo_id"] == 213

    @pytest.mark.asyncio
    async def test_lat_lng_query_skips_detect_location(
        self, yandex_client: AsyncMock
    ) -> None:
        provider = YandexDeliveryPickupPointProvider(yandex_client)

        await provider.list_pickup_points(
            PickupPointQuery(latitude=55.75, longitude=37.61, radius_km=5)
        )

        yandex_client.detect_location.assert_not_awaited()
        body = yandex_client.list_pickup_points.await_args.args[0]
        assert "latitude" in body and "geo_id" not in body

    @pytest.mark.asyncio
    async def test_picks_first_usable_geo_id(self, yandex_client: AsyncMock) -> None:
        yandex_client.detect_location.return_value = {
            "variants": [
                {"address": "no geo_id here"},
                {"geo_id": 2, "address": "Санкт-Петербург"},
            ]
        }
        provider = YandexDeliveryPickupPointProvider(yandex_client)

        await provider.list_pickup_points(PickupPointQuery(city="Санкт-Петербург"))

        body = yandex_client.list_pickup_points.await_args.args[0]
        assert body["geo_id"] == 2

    @pytest.mark.asyncio
    async def test_detect_failure_raises_descriptive_error(
        self, yandex_client: AsyncMock
    ) -> None:
        # detect_location 4xx → no geo_id → a clear "could not resolve"
        # error naming the city, not an unbounded listing request.
        yandex_client.detect_location.side_effect = ProviderHTTPError(
            status_code=404, message="not found"
        )
        provider = YandexDeliveryPickupPointProvider(yandex_client)

        with pytest.raises(ValueError, match="Could not resolve city 'Атлантида'"):
            await provider.list_pickup_points(PickupPointQuery(city="Атлантида"))
        yandex_client.list_pickup_points.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_variants_raises_descriptive_error(
        self, yandex_client: AsyncMock
    ) -> None:
        yandex_client.detect_location.return_value = {"variants": []}
        provider = YandexDeliveryPickupPointProvider(yandex_client)

        with pytest.raises(ValueError, match="Could not resolve city 'Нигде'"):
            await provider.list_pickup_points(PickupPointQuery(city="Нигде"))
        yandex_client.list_pickup_points.assert_not_awaited()


class TestGeoIdCache:
    @pytest.mark.asyncio
    async def test_resolved_geo_id_is_memoised(self, yandex_client: AsyncMock) -> None:
        yandex_client.detect_location.return_value = {
            "variants": [{"geo_id": 213, "address": "Москва"}]
        }
        provider = YandexDeliveryPickupPointProvider(yandex_client)

        await provider.list_pickup_points(PickupPointQuery(city="Москва"))
        await provider.list_pickup_points(PickupPointQuery(city="Москва"))

        # Second call serves geo_id from the memo — no extra round-trip.
        yandex_client.detect_location.assert_awaited_once_with("Москва")

    @pytest.mark.asyncio
    async def test_cache_evicts_least_recently_used(
        self, yandex_client: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.modules.logistics.infrastructure.providers.yandex_delivery import (
            pickup_point_provider as ppp,
        )

        monkeypatch.setattr(ppp, "_GEO_ID_CACHE_MAX", 2)
        # One detect response per expected round-trip; a 5th call would
        # raise StopIteration and fail the test loudly.
        yandex_client.detect_location.side_effect = [
            {"variants": [{"geo_id": 1}]},  # A
            {"variants": [{"geo_id": 2}]},  # B
            {"variants": [{"geo_id": 3}]},  # C — evicts A (LRU)
            {"variants": [{"geo_id": 1}]},  # A again — was evicted
        ]
        provider = YandexDeliveryPickupPointProvider(yandex_client)

        for city in ("A", "B", "C", "A"):
            await provider.list_pickup_points(PickupPointQuery(city=city))

        assert yandex_client.detect_location.await_count == 4
