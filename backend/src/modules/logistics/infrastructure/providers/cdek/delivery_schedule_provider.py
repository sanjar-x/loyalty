"""
CDEK delivery-schedule provider — implements ``IDeliveryScheduleProvider``.

Wraps:
- GET /v2/delivery/intervals (post-booking) — slots for an existing order.
- POST /v2/delivery/estimatedIntervals (pre-booking) — best-effort slots
  before the order is placed (used by the storefront for cart preview).
"""

from __future__ import annotations

import logging
from typing import Any

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    Address,
    DeliveryInterval,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient

logger = logging.getLogger(__name__)


class CdekDeliveryScheduleProvider:
    """CDEK implementation of ``IDeliveryScheduleProvider``."""

    def __init__(self, client: CdekClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def get_intervals(self, provider_shipment_id: str) -> list[DeliveryInterval]:
        async with self._client:
            data = await self._client.get_delivery_intervals(
                {"order_uuid": provider_shipment_id}
            )
        return _parse_intervals(data)

    async def get_estimated_intervals(
        self,
        origin: Address,
        destination: Address,
        tariff_code: int,
    ) -> list[DeliveryInterval]:
        body: dict[str, Any] = {
            "tariff_code": tariff_code,
            "from_location": _build_estimate_location(origin),
            "to_location": _build_estimate_location(destination),
        }
        async with self._client:
            data = await self._client.get_estimated_delivery_intervals(body)
        return _parse_intervals(data)


def _build_estimate_location(address: Address) -> dict[str, Any]:
    loc: dict[str, Any] = {}
    if address.metadata.get("cdek_city_code"):
        loc["code"] = int(address.metadata["cdek_city_code"])
    if address.postal_code:
        loc["postal_code"] = address.postal_code
    if address.country_code:
        loc["country_code"] = address.country_code
    if address.city:
        loc["city"] = address.city
    return loc


def _parse_intervals(data: dict) -> list[DeliveryInterval]:
    """Parse CDEK delivery-intervals response.

    Both ``/v2/delivery/intervals`` (post-booking) and
    ``/v2/delivery/estimatedIntervals`` (pre-booking) return a
    ``date_intervals`` array shaped as::

        [{"date": "2025-04-26",
          "time_intervals": [{"start_time": "09:00", "end_time": "12:00"}]}]
    """
    if not isinstance(data, dict):
        return []
    out: list[DeliveryInterval] = []
    date_intervals = data.get("date_intervals", [])
    if not isinstance(date_intervals, list):
        return out
    for entry in date_intervals:
        if not isinstance(entry, dict):
            continue
        date_str = entry.get("date")
        time_intervals = entry.get("time_intervals") or []
        if not isinstance(time_intervals, list):
            continue
        for slot in time_intervals:
            if not isinstance(slot, dict):
                continue
            start = slot.get("start_time")
            end = slot.get("end_time")
            if start and end:
                out.append(
                    DeliveryInterval(
                        start_time=str(start),
                        end_time=str(end),
                        date=str(date_str) if date_str else None,
                    )
                )
    return out
