"""
Yandex Delivery delivery-schedule provider — implements ``IDeliveryScheduleProvider``.

Wraps two endpoint groups:

- ``POST /api/b2b/platform/offers/info`` (1.03) — pre-booking delivery
  windows for a hypothetical shipment described by source / destination
  / packages.
- ``POST /api/b2b/platform/request/datetime_options`` (3.07) — delivery
  windows for an *already-booked* request, looking up the current
  destination from the order itself.

The CDEK-flavoured ``IDeliveryScheduleProvider.get_estimated_intervals``
signature accepts a numeric ``tariff_code``; for Yandex we map it to
the ``last_mile_policy`` value:

- ``1`` → ``time_interval`` (default — courier door delivery)
- ``2`` → ``self_pickup`` (pickup point)

Anything else falls back to ``time_interval``.
"""

from __future__ import annotations

import logging
from typing import Any

from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    ActualDeliveryInfo,
    Address,
    DeliveryInterval,
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
    build_offers_info_request,
    parse_datetime_options,
    parse_offer_info_intervals,
)

logger = logging.getLogger(__name__)


# Translates the cross-provider numeric tariff hint into Yandex's last-mile
# enum. ``1`` = door delivery (courier), ``2`` = pickup-point delivery —
# matches the order in which ``calculate_rates`` enumerates tariffs.
_TARIFF_CODE_TO_LAST_MILE: dict[int, str] = {
    1: LAST_MILE_COURIER,
    2: LAST_MILE_PICKUP,
}


class YandexDeliveryDeliveryScheduleProvider:
    """Yandex Delivery implementation of ``IDeliveryScheduleProvider``.

    Both calls return an empty list (rather than raising) when Yandex
    answers HTTP 400 ``no_delivery_options`` — that signals "no slots
    today", not a hard provider failure, so callers can present an
    empty calendar instead of an error toast.
    """

    def __init__(self, client: YandexDeliveryClient, config: dict[str, Any]) -> None:
        self._client = client
        self._config = config

    def provider_code(self) -> ProviderCode:
        return PROVIDER_YANDEX_DELIVERY

    async def get_intervals(self, provider_shipment_id: str) -> list[DeliveryInterval]:
        async with self._client:
            try:
                data = await self._client.request_datetime_options(provider_shipment_id)
            except ProviderHTTPError as exc:
                if exc.status_code == 400:
                    logger.debug(
                        "Yandex datetime_options: no slots for %s (%s)",
                        provider_shipment_id,
                        exc.message,
                    )
                    return []
                raise
        return parse_datetime_options(data)

    async def get_actual_delivery_info(
        self, provider_shipment_id: str
    ) -> ActualDeliveryInfo | None:
        """Fetch the carrier-confirmed delivery window (3.05).

        Returns ``None`` if Yandex reports the order has no actual
        info yet (e.g. status is ``DELIVERY_DELIVERED`` or pre-pickup
        states for which the endpoint returns 404 / 400).
        """
        async with self._client:
            try:
                data = await self._client.get_actual_info(provider_shipment_id)
            except ProviderHTTPError as exc:
                if exc.status_code in (400, 404):
                    return None
                raise
        return _parse_actual_info(data)

    async def get_estimated_intervals(
        self,
        origin: Address,
        destination: Address,
        tariff_code: int,
    ) -> list[DeliveryInterval]:
        last_mile = _TARIFF_CODE_TO_LAST_MILE.get(tariff_code, LAST_MILE_COURIER)
        # ``offers/info`` POST does not need a parcel weight to enumerate
        # *available* days, but the API still expects ``places`` with at
        # least one entry — we pass a 1-gram placeholder so callers can
        # query intervals before they have package data.
        body = build_offers_info_request(
            origin=origin,
            destination=destination,
            parcels=_PLACEHOLDER_PARCELS,
            config=self._config,
        )
        async with self._client:
            try:
                data = await self._client.offers_info(body, last_mile_policy=last_mile)
            except ProviderHTTPError as exc:
                if exc.status_code == 400:
                    logger.debug("Yandex offers/info: no slots (%s)", exc.message)
                    return []
                raise
        return parse_offer_info_intervals(data)


# Single placeholder parcel used by ``get_estimated_intervals`` when the
# caller is querying schedules without a concrete package context.
def _placeholder_parcels() -> list:
    from src.modules.logistics.domain.value_objects import Parcel, Weight

    return [Parcel(weight=Weight(grams=1))]


_PLACEHOLDER_PARCELS = _placeholder_parcels()


def _parse_actual_info(data: Any) -> ActualDeliveryInfo | None:
    """Translate ``GET /request/actual_info`` (3.05) into ActualDeliveryInfo.

    Yandex emits ``{"delivery_date": "YYYY-MM-DD",
    "delivery_interval": {"from": "10:00+03:00", "to": "23:00+03:00"}}``.

    The interval bounds are local times with a tz suffix; we strip the
    suffix to keep the shared shape as ``HH:MM`` plus a separate
    ``timezone_offset`` field. Returns ``None`` for unparseable
    responses so callers don't need to guard against partial payloads.
    """
    if not isinstance(data, dict):
        return None
    delivery_date = data.get("delivery_date")
    interval = data.get("delivery_interval")
    if not isinstance(delivery_date, str) or not isinstance(interval, dict):
        return None
    raw_from = interval.get("from")
    raw_to = interval.get("to")
    if not isinstance(raw_from, str) or not isinstance(raw_to, str):
        return None
    start_time, tz_from = _split_local_with_tz(raw_from)
    end_time, _tz_to = _split_local_with_tz(raw_to)
    return ActualDeliveryInfo(
        delivery_date=delivery_date,
        interval_start=start_time,
        interval_end=end_time,
        timezone_offset=tz_from,
    )


def _split_local_with_tz(value: str) -> tuple[str, str | None]:
    """Split ``"10:00+03:00"`` into (``"10:00"``, ``"+03:00"``)."""
    for sep in ("+", "-"):
        idx = value.find(sep, 1)
        if idx > 0:
            return value[:idx], value[idx:]
    return value, None
