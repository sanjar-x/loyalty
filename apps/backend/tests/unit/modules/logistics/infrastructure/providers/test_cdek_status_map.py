"""
Regression tests for the CDEK status map.

Two safety properties this test pins down (M-1, Wave 1):

* Unknown CDEK statuses fall back to **non-terminal** ``IN_TRANSIT`` —
  not ``EXCEPTION``. CDEK extends Приложение 1 over time; the previous
  ``EXCEPTION`` fallback combined with the FSM auto-transition hook in
  ``Shipment.append_tracking_event`` used to auto-FAIL a shipment the
  first time the carrier reported any new status code.

* ``RETURNED_TO_SENDER_CITY_WAREHOUSE`` and
  ``RETURNED_TO_TRANSIT_WAREHOUSE`` are **waystations** on the return
  leg, mapped to ``IN_TRANSIT`` — the parcel is still moving and may
  later land in the terminal ``RETURNED`` state. They are no longer
  ``EXCEPTION``.
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
        # Return waystations — parcel still in motion, not a terminal
        # failure (was EXCEPTION pre-M-1; auto-FAIL'd live returns).
        ("RETURNED_TO_SENDER_CITY_WAREHOUSE", TrackingStatus.IN_TRANSIT),
        ("RETURNED_TO_TRANSIT_WAREHOUSE", TrackingStatus.IN_TRANSIT),
    ],
)
def test_known_codes_map_to_expected_status(
    code: str, expected: TrackingStatus
) -> None:
    assert cdek_status_to_tracking(code) is expected


def test_unknown_codes_fall_back_to_in_transit() -> None:
    """Pre-M-1 the fallback was ``EXCEPTION`` — and EXCEPTION is in
    ``TERMINAL_FAILURE_TRACKING_STATUSES``, so the FSM auto-transition
    in ``Shipment.append_tracking_event`` would mark the shipment FAILED
    the first time CDEK extended Приложение 1. We now fall back to
    non-terminal ``IN_TRANSIT`` and log a warning instead.
    """
    assert cdek_status_to_tracking("MYSTERY_CODE") is TrackingStatus.IN_TRANSIT
    assert cdek_status_to_tracking("") is TrackingStatus.IN_TRANSIT


def test_in_transit_is_not_a_terminal_failure_status() -> None:
    """Guard against accidental re-classification of IN_TRANSIT as terminal
    (which would re-introduce the M-1 bug by the back door)."""
    from src.modules.logistics.domain.value_objects import (
        TERMINAL_CANCEL_TRACKING_STATUSES,
        TERMINAL_FAILURE_TRACKING_STATUSES,
    )

    assert TrackingStatus.IN_TRANSIT not in TERMINAL_FAILURE_TRACKING_STATUSES
    assert TrackingStatus.IN_TRANSIT not in TERMINAL_CANCEL_TRACKING_STATUSES
