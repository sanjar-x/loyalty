"""Unit tests for ``russian_carrier_status_map`` (LOG-002)."""

from __future__ import annotations

import pytest

from src.modules.logistics.domain.russian_carrier_status_map import (
    RussianCarrierAction,
    russian_carrier_status_map,
)
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    PROVIDER_DOBROPOST,
    PROVIDER_RUSSIAN_POST,
    PROVIDER_YANDEX_DELIVERY,
    TrackingStatus,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "provider", [PROVIDER_CDEK, PROVIDER_YANDEX_DELIVERY, PROVIDER_RUSSIAN_POST]
)
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (TrackingStatus.IN_TRANSIT, RussianCarrierAction.IN_LAST_MILE),
        (TrackingStatus.OUT_FOR_DELIVERY, RussianCarrierAction.OUT_FOR_DELIVERY),
        (TrackingStatus.READY_FOR_PICKUP, RussianCarrierAction.AT_PICKUP_POINT),
        (TrackingStatus.DELIVERED, RussianCarrierAction.DELIVERED),
        (TrackingStatus.RETURNED, RussianCarrierAction.RETURN_TO_SENDER),
        (TrackingStatus.EXCEPTION, RussianCarrierAction.RETURN_TO_SENDER),
    ],
)
def test_mapped_statuses(
    provider: str, status: TrackingStatus, expected: RussianCarrierAction
) -> None:
    assert russian_carrier_status_map(status, provider) is expected


@pytest.mark.parametrize(
    "status",
    [
        # Statuses without an Order action — produce None.
        TrackingStatus.CREATED,
        TrackingStatus.ACCEPTED,
        TrackingStatus.CUSTOMS,
        TrackingStatus.LOST,
        TrackingStatus.ATTEMPT_FAILED,
        TrackingStatus.CANCELLED,
    ],
)
def test_unmapped_statuses_return_none(status: TrackingStatus) -> None:
    assert russian_carrier_status_map(status, PROVIDER_CDEK) is None


@pytest.mark.parametrize(
    "status",
    [
        TrackingStatus.IN_TRANSIT,
        TrackingStatus.READY_FOR_PICKUP,
        TrackingStatus.DELIVERED,
        TrackingStatus.RETURNED,
        TrackingStatus.EXCEPTION,
    ],
)
def test_dobropost_provider_always_returns_none(status: TrackingStatus) -> None:
    """DobroPost cross-border owns its own ingest pipeline — no russian-carrier
    action should ever fire for it."""
    assert russian_carrier_status_map(status, PROVIDER_DOBROPOST) is None


def test_action_string_values_match_consumer_branches() -> None:
    """Locks the canonical-action vocabulary against the consumer's
    ``normalized.upper()`` branches (in
    ``order.application.consumers.logistics_events.RussianCarrierTrackingConsumer.handle``).
    Renaming an action MUST fail this test loudly so a producer/consumer
    drift can't slip through."""
    assert RussianCarrierAction.IN_LAST_MILE.value == "IN_TRANSIT"
    assert RussianCarrierAction.OUT_FOR_DELIVERY.value == "OUT_FOR_DELIVERY"
    assert RussianCarrierAction.AT_PICKUP_POINT.value == "AT_PICKUP_POINT"
    assert RussianCarrierAction.DELIVERED.value == "DELIVERED"
    assert RussianCarrierAction.RETURN_TO_SENDER.value == "RETURN_TO_SENDER"
