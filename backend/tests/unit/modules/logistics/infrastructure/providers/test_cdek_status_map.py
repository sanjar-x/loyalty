"""
Regression tests: CDEK status code map covers the full Приложение 15
status set, so no real-world status falls through to ``EXCEPTION`` by
accident.
"""

from __future__ import annotations

import pytest

from src.modules.logistics.domain.value_objects import TrackingStatus
from src.modules.logistics.infrastructure.providers.cdek.constants import (
    cdek_status_to_tracking,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "code,expected",
    [
        ("CREATED", TrackingStatus.CREATED),
        ("REGISTERED", TrackingStatus.CREATED),
        ("ACCEPTED", TrackingStatus.ACCEPTED),
        ("RECEIVED_AT_SHIPMENT_WAREHOUSE", TrackingStatus.ACCEPTED),
        ("READY_TO_SHIP_AT_SENDING_OFFICE", TrackingStatus.ACCEPTED),
        ("TAKEN_BY_TRANSPORTER", TrackingStatus.IN_TRANSIT),
        ("TAKEN_BY_TRANSPORTER_FROM_TRANSIT_CITY", TrackingStatus.IN_TRANSIT),
        ("PASSED_TO_TRANSIT_CARRIER", TrackingStatus.IN_TRANSIT),
        ("SHIPPED_TO_DESTINATION", TrackingStatus.IN_TRANSIT),
        ("IN_CUSTOMS_INTERNATIONAL", TrackingStatus.CUSTOMS),
        ("IN_CUSTOMS_LOCAL", TrackingStatus.CUSTOMS),
        ("SUBMITTED_TO_CUSTOMS", TrackingStatus.CUSTOMS),
        ("RELEASED_BY_CUSTOMS", TrackingStatus.IN_TRANSIT),
        ("CUSTOMS_COMPLETE", TrackingStatus.IN_TRANSIT),
        ("ACCEPTED_AT_PICK_UP_POINT", TrackingStatus.READY_FOR_PICKUP),
        ("POSTOMAT_POSTED", TrackingStatus.READY_FOR_PICKUP),
        ("POSTOMAT_RECEIVED", TrackingStatus.DELIVERED),
        ("TAKEN_BY_COURIER", TrackingStatus.OUT_FOR_DELIVERY),
        ("TAKEN_BY_COURIER_FROM_WAREHOUSE", TrackingStatus.OUT_FOR_DELIVERY),
        ("DELIVERED", TrackingStatus.DELIVERED),
        ("RETURNED_TO_RECIPIENT_CITY_WAREHOUSE", TrackingStatus.ATTEMPT_FAILED),
        ("NOT_DELIVERED", TrackingStatus.EXCEPTION),
        ("INVALID", TrackingStatus.EXCEPTION),
        ("DELETED", TrackingStatus.CANCELLED),
        ("RETURNED_TO_SENDER", TrackingStatus.RETURNED),
        ("RETURNED_TO_SENDER_CITY_WAREHOUSE", TrackingStatus.EXCEPTION),
    ],
)
def test_known_codes_map_to_expected_status(
    code: str, expected: TrackingStatus
) -> None:
    assert cdek_status_to_tracking(code) is expected


def test_unknown_codes_fall_back_to_exception() -> None:
    assert cdek_status_to_tracking("MYSTERY_CODE") is TrackingStatus.EXCEPTION
    assert cdek_status_to_tracking("") is TrackingStatus.EXCEPTION
