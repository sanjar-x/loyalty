"""Unit tests for the Redis pickup-point cache serialisation helpers.

Round-trip coverage so adding a new ``PickupPoint`` field can't silently
drop on the way through Redis (the cache is read by
``QuoteForPickupPointHandler`` — a missing field there means the quote
sees a different shape than the listing did).
"""

from __future__ import annotations

import pytest

from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    Address,
    PickupPoint,
    PickupPointServices,
    PickupPointType,
)
from src.modules.logistics.infrastructure.adapters.pickup_point_cache import (
    _payload_to_pickup_point,
    _pickup_point_to_payload,
)

pytestmark = pytest.mark.unit


def _point(services: PickupPointServices | None) -> PickupPoint:
    return PickupPoint(
        provider_code=PROVIDER_YANDEX_DELIVERY,
        external_id="pvz-1",
        name="ПВЗ",
        pickup_point_type=PickupPointType.PVZ,
        address=Address(
            country_code="RU",
            city="Москва",
            latitude=55.66,
            longitude=37.51,
            metadata={"platform_station_id": "pvz-1"},
        ),
        services=services,
    )


def test_services_round_trips_through_cache() -> None:
    original = _point(
        PickupPointServices(
            is_fitting_allowed=True,
            is_partial_refuse_allowed=False,
            is_paperless_pickup_allowed=True,
            is_unboxing_allowed=False,
        )
    )
    restored = _payload_to_pickup_point(_pickup_point_to_payload(original))
    assert restored is not None
    assert restored.services == original.services


def test_missing_services_stays_none() -> None:
    restored = _payload_to_pickup_point(_pickup_point_to_payload(_point(None)))
    assert restored is not None
    assert restored.services is None


def test_legacy_payload_without_services_decodes() -> None:
    # Records cached before the field was added must still load.
    payload = _pickup_point_to_payload(_point(None))
    payload.pop("services")
    restored = _payload_to_pickup_point(payload)
    assert restored is not None
    assert restored.services is None
