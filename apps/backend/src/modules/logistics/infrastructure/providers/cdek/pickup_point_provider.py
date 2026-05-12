"""
CDEK pickup point provider — implements ``IPickupPointProvider``.

Lists CDEK delivery points (PVZ / postamats) from the
``GET /v2/deliverypoints`` endpoint with automatic pagination.

Geographic radius search (``query.latitude/longitude/radius_km``) is
*not* supported by the CDEK API — it doesn't accept those parameters.
Instead we apply an in-memory haversine filter on the parsed points.
"""

from __future__ import annotations

import math

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

_EARTH_RADIUS_KM = 6371.0


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
        raw = await self._client.list_all_delivery_points(params)
        points = parse_delivery_points(raw)
        return _filter_by_radius(
            points,
            latitude=query.latitude,
            longitude=query.longitude,
            radius_km=query.radius_km,
        )


def _filter_by_radius(
    points: list[PickupPoint],
    *,
    latitude: float | None,
    longitude: float | None,
    radius_km: int | None,
) -> list[PickupPoint]:
    """Filter ``points`` to those within ``radius_km`` of (lat, lon).

    CDEK does not implement server-side radius search, so apply the
    filter locally. Points without coordinates are excluded when a
    radius is requested. No-op if any of lat / lon / radius is missing.
    """
    if latitude is None or longitude is None or radius_km is None:
        return points
    return [
        point
        for point in points
        if point.address.latitude is not None
        and point.address.longitude is not None
        and _haversine_km(
            latitude,
            longitude,
            point.address.latitude,
            point.address.longitude,
        )
        <= radius_km
    ]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points, in kilometres."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))
