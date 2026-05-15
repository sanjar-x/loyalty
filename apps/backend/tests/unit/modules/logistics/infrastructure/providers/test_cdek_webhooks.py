"""
Phase-1 regression tests for the CDEK webhook layer:

* ``CDEK_WEBHOOK_TYPES`` matches the current CDEK API ``WebhookDto``
  enum — the legacy phantom codes (``DOWNLOAD_PHOTO`` / ``DELAYED`` /
  ``CD_REQUEST`` / ``RECEIVE_FAIL``) are gone.
* ``parse_webhook_body`` dispatches by ``type``: ORDER_STATUS prefers
  the canonical ``code`` over the deprecated ``status_code`` and folds
  ``status_reason_code`` into the description; DELIV_PROBLEM becomes a
  non-terminal ATTEMPT_FAILED event; ORDER_MODIFIED / unknown types are
  skipped.
"""

from __future__ import annotations

import json

import pytest

from src.modules.logistics.domain.value_objects import TrackingStatus
from src.modules.logistics.infrastructure.providers.cdek.constants import (
    CDEK_MAX_WEBHOOK_SUBSCRIPTIONS,
    CDEK_WEBHOOK_AUTO_SUBSCRIBE,
    CDEK_WEBHOOK_TYPES,
)
from src.modules.logistics.infrastructure.providers.cdek.mappers import (
    parse_webhook_body,
)

pytestmark = pytest.mark.unit


class TestWebhookTypeConstants:
    def test_types_match_current_api_enum(self) -> None:
        expected = {
            "ORDER_STATUS",
            "ORDER_MODIFIED",
            "PRINT_FORM",
            "RECEIPT",
            "PREALERT_CLOSED",
            "ACCOMPANYING_WAYBILL",
            "OFFICE_AVAILABILITY",
            "DELIV_PROBLEM",
            "DELIV_AGREEMENT",
            "COURIER_INFO",
        }
        assert set(CDEK_WEBHOOK_TYPES) == expected

    def test_legacy_phantom_types_are_gone(self) -> None:
        for phantom in ("DOWNLOAD_PHOTO", "DELAYED", "CD_REQUEST", "RECEIVE_FAIL"):
            assert phantom not in CDEK_WEBHOOK_TYPES

    def test_auto_subscribe_is_within_cap_and_valid(self) -> None:
        assert len(CDEK_WEBHOOK_AUTO_SUBSCRIBE) <= CDEK_MAX_WEBHOOK_SUBSCRIPTIONS
        assert set(CDEK_WEBHOOK_AUTO_SUBSCRIBE) <= CDEK_WEBHOOK_TYPES


def _webhook(type_: str, uuid: str, attributes: dict) -> bytes:
    return json.dumps(
        {
            "type": type_,
            "date_time": "2026-05-01T10:00:00+03:00",
            "uuid": uuid,
            "attributes": attributes,
        }
    ).encode()


class TestOrderStatusWebhook:
    def test_prefers_canonical_code_over_deprecated_status_code(self) -> None:
        body = _webhook(
            "ORDER_STATUS",
            "order-1",
            {
                "is_return": False,
                "code": "DELIVERED",
                "status_code": "4",  # deprecated — must NOT win
                "status_date_time": "2026-05-01T10:00:00+03:00",
                "city_name": "Москва",
            },
        )

        result = parse_webhook_body(body)

        assert len(result) == 1
        sid, events = result[0]
        assert sid == "order-1"
        assert len(events) == 1
        event = events[0]
        assert event.status is TrackingStatus.DELIVERED
        assert event.provider_status_code == "DELIVERED"
        # Приложение 1 name, not the raw code or a reason code.
        assert event.provider_status_name == "Вручён"
        assert event.location == "Москва"

    def test_reason_code_folded_into_description(self) -> None:
        body = _webhook(
            "ORDER_STATUS",
            "order-2",
            {
                "code": "NOT_DELIVERED",
                "status_reason_code": "3",
                "status_date_time": "2026-05-01T10:00:00+03:00",
            },
        )

        _sid, events = parse_webhook_body(body)[0]

        assert events[0].status is TrackingStatus.EXCEPTION
        assert events[0].description == "Не вручён — Возврат: адресат не проживает"

    def test_return_flow_events_are_skipped(self) -> None:
        body = _webhook(
            "ORDER_STATUS",
            "order-3",
            {
                "is_return": True,
                "code": "DELIVERED",
                "status_date_time": "2026-05-01T10:00:00+03:00",
            },
        )

        assert parse_webhook_body(body) == []

    def test_missing_code_or_uuid_yields_no_events(self) -> None:
        body = _webhook("ORDER_STATUS", "", {"code": "DELIVERED"})
        assert parse_webhook_body(body) == []


class TestDelivProblemWebhook:
    def test_maps_to_non_terminal_attempt_failed_event(self) -> None:
        body = _webhook(
            "DELIV_PROBLEM",
            "order-4",
            {
                "cdek_number": "1100",
                "code": "13",
                "create_date": "2026-05-01T11:00:00+03:00",
            },
        )

        result = parse_webhook_body(body)

        assert len(result) == 1
        sid, events = result[0]
        assert sid == "order-4"
        event = events[0]
        # ATTEMPT_FAILED is non-terminal — the shipment FSM is not
        # dragged to FAILED by a retryable delivery problem.
        assert event.status is TrackingStatus.ATTEMPT_FAILED
        assert event.provider_status_code == "DELIV_PROBLEM:13"
        assert event.description == "Проблема доставки: Контактное лицо отсутствует"

    def test_unknown_problem_code_falls_back_gracefully(self) -> None:
        body = _webhook(
            "DELIV_PROBLEM",
            "order-5",
            {"code": "999", "create_date": "2026-05-01T11:00:00+03:00"},
        )

        _sid, events = parse_webhook_body(body)[0]

        assert events[0].status is TrackingStatus.ATTEMPT_FAILED
        assert events[0].provider_status_name == "Проблема доставки"


class TestSkippedWebhookTypes:
    def test_order_modified_is_observed_but_emits_no_event(self) -> None:
        body = _webhook(
            "ORDER_MODIFIED",
            "order-6",
            {
                "modification_type": "DELIVERY_SUM_CHANGED",
                "new_value": {"type": "FLOAT", "value": "550"},
            },
        )

        assert parse_webhook_body(body) == []

    @pytest.mark.parametrize(
        "event_type",
        ["PRINT_FORM", "DELIV_AGREEMENT", "OFFICE_AVAILABILITY", "COURIER_INFO", ""],
    )
    def test_other_types_are_skipped(self, event_type: str) -> None:
        body = _webhook(event_type, "order-7", {})
        assert parse_webhook_body(body) == []

    def test_non_dict_body_is_skipped(self) -> None:
        assert parse_webhook_body(b'"just a string"') == []
