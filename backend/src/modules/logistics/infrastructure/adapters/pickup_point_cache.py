"""Redis-backed implementation of :class:`IPickupPointResolver`.

When the storefront renders the map, ``ListPickupPointsHandler`` fans out
to every provider and returns the union. The frontend remembers only the
``(provider_code, external_id)`` pair per marker, so when the user clicks
one we need to recover the full ``PickupPoint`` (address, station_id /
pvz_code metadata) on the server to build a delivery-quote request.

Re-fetching the full provincial pickup-point catalogue per click would
melt CDEK's / Yandex's rate-limited APIs (BRD risk: «Один из двух
провайдеров (CDEK / Yandex) недоступен»). Instead, ``ListPickupPointsHandler``
now warms this cache after every successful provider call, and
``QuoteForPickupPointHandler`` reads from it.

A 24-hour TTL is generous: pickup-point data churns slowly (new branches,
schedule changes) and the cache invalidates naturally via TTL. If the
operator deactivates a point in the carrier system mid-day, the worst
outcome is a quote against a non-existent point — the booking call will
fail with a clear provider error and the customer is told to pick another.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.modules.logistics.domain.interfaces import IPickupPointResolver
from src.modules.logistics.domain.value_objects import (
    Address,
    Dimensions,
    PickupPoint,
    PickupPointType,
    ProviderCode,
)
from src.shared.interfaces.cache import ICacheService

# 24 hours per BRD diagram (LOG → PRV: GET /v2/deliverypoints (кэш 24ч)).
_PICKUP_POINT_TTL_SECONDS = 24 * 60 * 60
_KEY_PREFIX = "logistics:pickup_point:"

logger = logging.getLogger(__name__)


class RedisPickupPointResolver(IPickupPointResolver):
    """Persists pickup points serialised as JSON in Redis (or any ``ICacheService``).

    Storage shape: one key per ``(provider_code, external_id)``. Bulk
    reads happen one-key-at-a-time because the typical click path
    resolves a single point — there is no need for ``MGET``-style fan-in.
    Bulk writes use ``set_many`` so warming a fresh map response stays a
    single Redis round-trip.
    """

    def __init__(self, cache: ICacheService) -> None:
        self._cache = cache

    async def resolve(
        self,
        provider_code: ProviderCode,
        external_id: str,
    ) -> PickupPoint | None:
        if not provider_code or not external_id:
            return None
        raw = await self._cache.get(_make_key(provider_code, external_id))
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            logger.warning(
                "Cached pickup-point JSON is malformed; treating as miss",
                extra={"provider_code": provider_code, "external_id": external_id},
            )
            return None
        return _payload_to_pickup_point(payload)

    async def remember_many(self, points: list[PickupPoint]) -> None:
        if not points:
            return
        items: dict[str, str] = {}
        for point in points:
            if not point.provider_code or not point.external_id:
                # Defensive: the provider returned a malformed entry; skip
                # rather than poison the cache. Mappers already filter
                # most of this — but a third-party adapter could emit one.
                continue
            items[_make_key(point.provider_code, point.external_id)] = json.dumps(
                _pickup_point_to_payload(point), ensure_ascii=False
            )
        if not items:
            return
        await self._cache.set_many(items, ttl=_PICKUP_POINT_TTL_SECONDS)


# ---------------------------------------------------------------------------
# Serialisation helpers — symmetric pair, kept module-private.
# ---------------------------------------------------------------------------


def _make_key(provider_code: ProviderCode, external_id: str) -> str:
    return f"{_KEY_PREFIX}{provider_code}:{external_id}"


def _pickup_point_to_payload(point: PickupPoint) -> dict[str, Any]:
    return {
        "provider_code": point.provider_code,
        "external_id": point.external_id,
        "name": point.name,
        "pickup_point_type": point.pickup_point_type.value,
        "address": _address_to_payload(point.address),
        "work_schedule": point.work_schedule,
        "phone": point.phone,
        "is_cash_allowed": point.is_cash_allowed,
        "is_card_allowed": point.is_card_allowed,
        "weight_limit_grams": point.weight_limit_grams,
        "dimensions_limit": (
            {
                "length_cm": point.dimensions_limit.length_cm,
                "width_cm": point.dimensions_limit.width_cm,
                "height_cm": point.dimensions_limit.height_cm,
            }
            if point.dimensions_limit
            else None
        ),
    }


def _address_to_payload(address: Address) -> dict[str, Any]:
    return {
        "country_code": address.country_code,
        "city": address.city,
        "region": address.region,
        "postal_code": address.postal_code,
        "street": address.street,
        "house": address.house,
        "apartment": address.apartment,
        "subdivision_code": address.subdivision_code,
        "latitude": address.latitude,
        "longitude": address.longitude,
        "raw_address": address.raw_address,
        "metadata": dict(address.metadata),
    }


def _payload_to_pickup_point(data: dict[str, Any]) -> PickupPoint | None:
    try:
        address_data = data["address"]
        dims_data = data.get("dimensions_limit")
        return PickupPoint(
            provider_code=data["provider_code"],
            external_id=data["external_id"],
            name=data["name"],
            pickup_point_type=PickupPointType(data["pickup_point_type"]),
            address=Address(
                country_code=address_data["country_code"],
                city=address_data["city"],
                region=address_data.get("region"),
                postal_code=address_data.get("postal_code"),
                street=address_data.get("street"),
                house=address_data.get("house"),
                apartment=address_data.get("apartment"),
                subdivision_code=address_data.get("subdivision_code"),
                latitude=address_data.get("latitude"),
                longitude=address_data.get("longitude"),
                raw_address=address_data.get("raw_address"),
                metadata=dict(address_data.get("metadata") or {}),
            ),
            work_schedule=data.get("work_schedule"),
            phone=data.get("phone"),
            is_cash_allowed=bool(data.get("is_cash_allowed", False)),
            is_card_allowed=bool(data.get("is_card_allowed", False)),
            weight_limit_grams=data.get("weight_limit_grams"),
            dimensions_limit=(
                Dimensions(
                    length_cm=int(dims_data["length_cm"]),
                    width_cm=int(dims_data["width_cm"]),
                    height_cm=int(dims_data["height_cm"]),
                )
                if dims_data
                else None
            ),
        )
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Cached pickup-point payload could not be rebuilt: %s", exc)
        return None


__all__ = ["RedisPickupPointResolver"]
