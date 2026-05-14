"""
Yandex Delivery pickup point provider — implements ``IPickupPointProvider``.

Lists pickup and drop-off points via POST /pickup-points/list.

A bare ``city`` string is not a valid filter for ``/pickup-points/list``
— Yandex needs a numeric ``geo_id``. When the query carries no lat/lng
box, this provider resolves ``city`` → ``geo_id`` via the
``location/detect`` endpoint (2.01) before listing, so a city-level
query stays bounded instead of pulling the entire catalogue. Resolved
ids are memoised in a small bounded LRU: ``geo_id`` values are stable,
so no TTL is needed, and ``query.city`` is free-text storefront input,
so the cache is size-capped to stay DoS-safe.
"""

from collections import OrderedDict

import structlog

from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    PickupPoint,
    PickupPointQuery,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError
from src.modules.logistics.infrastructure.providers.yandex_delivery.client import (
    YandexDeliveryClient,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.mappers import (
    build_pickup_points_request,
    parse_pickup_points,
)

logger = structlog.get_logger(__name__)

# Upper bound on the city → geo_id memo. ``query.city`` is free-text
# storefront input, so the cache is size-capped to stay DoS-safe.
_GEO_ID_CACHE_MAX = 512


class YandexDeliveryPickupPointProvider:
    """Yandex Delivery implementation of ``IPickupPointProvider``."""

    def __init__(self, client: YandexDeliveryClient) -> None:
        self._client = client
        # The provider is APP-scoped, so the memo lives for the process
        # lifetime; an admin registry refresh builds a fresh instance.
        self._geo_id_cache: OrderedDict[str, int] = OrderedDict()

    def provider_code(self) -> ProviderCode:
        return PROVIDER_YANDEX_DELIVERY

    async def list_pickup_points(self, query: PickupPointQuery) -> list[PickupPoint]:
        geo_id = await self._resolve_geo_id(query)
        body = build_pickup_points_request(query, geo_id=geo_id)
        data = await self._client.list_pickup_points(body)
        return parse_pickup_points(data)

    async def _resolve_geo_id(self, query: PickupPointQuery) -> int | None:
        """Resolve ``query.city`` → ``geo_id`` via ``location/detect`` (2.01).

        Returns:
            ``None`` when no resolution is needed — the query already
            carries a lat/lng box (which bounds the response on its own),
            or carries neither city nor box (``build_pickup_points_request``
            then raises the generic "needs a bound" error). Otherwise the
            resolved ``geo_id`` for the query's ``city``.

        Raises:
            ValueError: the query carries a ``city`` that ``location/detect``
                could not resolve — issuing the listing anyway would pull
                the unbounded catalogue, so the caller must instead supply
                a lat/lng box.
        """
        if query.latitude is not None and query.longitude is not None:
            return None
        city = query.city
        if not city:
            return None

        cached = self._geo_id_cache.get(city)
        if cached is not None:
            self._geo_id_cache.move_to_end(city)
            return cached

        geo_id = await self._detect_geo_id(city)
        if geo_id is None:
            raise ValueError(
                f"Could not resolve city {city!r} to a Yandex geo_id; "
                "supply latitude+longitude to bound the pickup-point query"
            )
        self._remember_geo_id(city, geo_id)
        return geo_id

    async def _detect_geo_id(self, city: str) -> int | None:
        """Call ``location/detect`` and extract the first usable ``geo_id``.

        The first variant is the city-level match for a plain city name;
        Yandex only returns multiple variants for ambiguous *fragments*.
        Returns ``None`` (and logs) on a provider 4xx or an empty /
        malformed variant list, so the caller can raise a clean error.
        """
        try:
            data = await self._client.detect_location(city)
        except ProviderHTTPError as exc:
            logger.warning(
                "yandex.detect_location_failed",
                city=city,
                status_code=exc.status_code,
            )
            return None

        variants = data.get("variants", []) if isinstance(data, dict) else []
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            geo_id = variant.get("geo_id")
            if isinstance(geo_id, int):
                return geo_id

        logger.warning("yandex.detect_location_no_geo_id", city=city)
        return None

    def _remember_geo_id(self, city: str, geo_id: int) -> None:
        """Memoise ``city`` → ``geo_id``, evicting the least-recently-used
        entry once the cache exceeds ``_GEO_ID_CACHE_MAX``.

        Concurrent cache misses for the same city are benign — both
        coroutines resolve to the same stable ``geo_id`` and the second
        write merely refreshes the entry.
        """
        cache = self._geo_id_cache
        cache[city] = geo_id
        cache.move_to_end(city)
        while len(cache) > _GEO_ID_CACHE_MAX:
            cache.popitem(last=False)
