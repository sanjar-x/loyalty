"""
Regression tests for the Yandex Delivery status mapping.

The critical guarantee: an *unknown* Yandex status must map to a
*non-terminal* ``TrackingStatus``. ``_map_yandex_status`` previously
defaulted to ``EXCEPTION``, which is a member of
``TERMINAL_FAILURE_TRACKING_STATUSES`` — so any newly-introduced or
rarely-seen Yandex status would make ``Shipment.append_tracking_event``
auto-transition the shipment to ``FAILED`` and emit
``ShipmentDeliveryFailedEvent``.
"""

from __future__ import annotations

import pytest

from src.modules.logistics.domain.value_objects import (
    TERMINAL_FAILURE_TRACKING_STATUSES,
    TrackingStatus,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.constants import (
    YANDEX_STATUS_MAP,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.mappers import (
    _map_yandex_status,
)

pytestmark = pytest.mark.unit


class TestKnownStatuses:
    @pytest.mark.parametrize(
        "yandex_status,expected",
        [
            ("DRAFT", TrackingStatus.CREATED),
            ("CREATED", TrackingStatus.ACCEPTED),
            ("SORTING_CENTER_AT_START", TrackingStatus.IN_TRANSIT),
            ("DELIVERY_TRANSPORTATION_RECIPIENT", TrackingStatus.OUT_FOR_DELIVERY),
            ("DELIVERY_ARRIVED_PICKUP_POINT", TrackingStatus.READY_FOR_PICKUP),
            ("DELIVERY_DELIVERED", TrackingStatus.DELIVERED),
            ("PARTICULARLY_DELIVERED", TrackingStatus.DELIVERED),
            ("DELIVERY_ATTEMPT_FAILED", TrackingStatus.ATTEMPT_FAILED),
            ("RETURN_RETURNED", TrackingStatus.RETURNED),
            ("CANCELLED", TrackingStatus.CANCELLED),
            ("VALIDATING_ERROR", TrackingStatus.EXCEPTION),
        ],
    )
    def test_known_status_maps_verbatim(
        self, yandex_status: str, expected: TrackingStatus
    ) -> None:
        assert _map_yandex_status(yandex_status) is expected

    def test_every_table_entry_round_trips(self) -> None:
        # Whatever is in the table, the helper must return it unchanged —
        # the unknown-default branch must never shadow a real mapping.
        for code, expected in YANDEX_STATUS_MAP.items():
            assert _map_yandex_status(code) is expected


class TestUnknownStatus:
    @pytest.mark.parametrize(
        "unknown",
        ["", "SOME_BRAND_NEW_STATUS", "delivery_delivered", "lowercase_typo"],
    )
    def test_unknown_status_is_non_terminal(self, unknown: str) -> None:
        mapped = _map_yandex_status(unknown)
        # The whole point: an unrecognised status must not be able to
        # auto-fail a shipment.
        assert mapped not in TERMINAL_FAILURE_TRACKING_STATUSES

    def test_unknown_status_defaults_to_in_transit(self) -> None:
        assert _map_yandex_status("WHO_KNOWS") is TrackingStatus.IN_TRANSIT
