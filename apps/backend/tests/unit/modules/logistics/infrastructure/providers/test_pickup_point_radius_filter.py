"""
Regression tests: ``CdekPickupPointProvider`` applies a haversine
radius filter client-side because CDEK ``/v2/deliverypoints`` does not
accept ``latitude`` / ``longitude`` / ``radius`` query parameters.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.domain.value_objects import (
    Address,
    PickupPoint,
    PickupPointQuery,
    PickupPointType,
)
from src.modules.logistics.infrastructure.providers.cdek.pickup_point_provider import (
    CdekPickupPointProvider,
    _filter_by_radius,
    _haversine_km,
)

pytestmark = pytest.mark.unit


def _point(
    code: str, lat: float | None = None, lon: float | None = None
) -> PickupPoint:
    return PickupPoint(
        provider_code="cdek",
        external_id=code,
        name=f"Office {code}",
        pickup_point_type=PickupPointType.PVZ,
        address=Address(
            country_code="RU",
            city="Moscow",
            latitude=lat,
            longitude=lon,
        ),
        is_cash_allowed=True,
        is_card_allowed=True,
    )


class TestHaversineDistance:
    def test_zero_distance_for_same_point(self) -> None:
        assert _haversine_km(55.7558, 37.6173, 55.7558, 37.6173) == pytest.approx(
            0.0, abs=1e-6
        )

    def test_moscow_to_st_petersburg_about_633km(self) -> None:
        # Moscow → St. Petersburg, ground truth ~633 km.
        distance = _haversine_km(55.7558, 37.6173, 59.9343, 30.3351)
        assert 625 <= distance <= 645


class TestRadiusFilter:
    def test_no_filter_when_lat_lon_or_radius_missing(self) -> None:
        points = [_point("A", 55.0, 37.0), _point("B", 60.0, 30.0)]
        # All three combinations of "missing" arguments leave the list intact.
        assert (
            _filter_by_radius(points, latitude=None, longitude=37.0, radius_km=10)
            == points
        )
        assert (
            _filter_by_radius(points, latitude=55.0, longitude=None, radius_km=10)
            == points
        )
        assert (
            _filter_by_radius(points, latitude=55.0, longitude=37.0, radius_km=None)
            == points
        )

    def test_drops_points_without_coordinates_when_filtering(self) -> None:
        kept = _point("near", 55.7558, 37.6173)
        no_coords = _point("blank", None, None)
        filtered = _filter_by_radius(
            [kept, no_coords],
            latitude=55.7558,
            longitude=37.6173,
            radius_km=5,
        )
        assert filtered == [kept]

    def test_keeps_only_points_within_radius(self) -> None:
        moscow = _point("A", 55.7558, 37.6173)
        spb = _point("B", 59.9343, 30.3351)
        filtered = _filter_by_radius(
            [moscow, spb],
            latitude=55.7558,
            longitude=37.6173,
            radius_km=100,
        )
        assert filtered == [moscow]


class TestProviderUsesFilter:
    @pytest.mark.asyncio
    async def test_list_pickup_points_applies_radius_filter(self) -> None:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = False
        # Two raw CDEK offices — one in Moscow, one in St. Petersburg.
        client.list_all_delivery_points.return_value = [
            {
                "code": "MSK1",
                "name": "Moscow PVZ",
                "type": "PVZ",
                "location": {
                    "country_code": "RU",
                    "city": "Moscow",
                    "latitude": 55.7558,
                    "longitude": 37.6173,
                },
                "have_cash": True,
                "have_cashless": True,
            },
            {
                "code": "SPB1",
                "name": "SPb PVZ",
                "type": "PVZ",
                "location": {
                    "country_code": "RU",
                    "city": "St. Petersburg",
                    "latitude": 59.9343,
                    "longitude": 30.3351,
                },
                "have_cash": True,
                "have_cashless": True,
            },
        ]
        provider = CdekPickupPointProvider(client)

        query = PickupPointQuery(
            country_code="RU",
            latitude=55.7558,
            longitude=37.6173,
            radius_km=100,
        )

        points = await provider.list_pickup_points(query)
        assert [p.external_id for p in points] == ["MSK1"]
