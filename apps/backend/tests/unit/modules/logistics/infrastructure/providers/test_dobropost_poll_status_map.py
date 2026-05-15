"""
M-1 regression test: DobroPost poll path is symmetric with the webhook
path on unknown ``status_id``.

Before M-1 the poll-mapper (``parse_list_shipment_response``) fell back
to ``TrackingStatus.EXCEPTION`` for any ``status_id`` not in
``DOBROPOST_STATUS_MAP``. Combined with the FSM auto-transition hook in
``Shipment.append_tracking_event`` (``EXCEPTION`` ∈
``TERMINAL_FAILURE_TRACKING_STATUSES``), the first time DobroPost shipped
a new status_id the polling backstop — which is the explicit safety net
for missed webhooks — would auto-FAIL every live shipment that hit it.

The webhook path has always done the right thing: ``parse_status_update_event``
calls ``dobropost_name_to_status_id`` which returns ``None`` for
unknowns, and the event is dropped. Now both paths skip + warn.
"""

from __future__ import annotations

import pytest

from src.modules.logistics.infrastructure.providers.dobropost.mappers import (
    parse_list_shipment_response,
)

pytestmark = pytest.mark.unit


def _row(dp_id: int, status_id: str, status_name: str = "x") -> dict:
    return {
        "id": dp_id,
        "status": {
            "id": int(status_id) if status_id.isdigit() else status_id,
            "name": status_name,
        },
        "statusDate": "2026-05-15T10:00:00+0300",
    }


class TestPollUnknownStatusSkipped:
    def test_unknown_status_id_yields_no_events(self) -> None:
        """Unknown status_id must NOT produce an EXCEPTION TrackingEvent —
        otherwise the FSM auto-transition would FAIL the shipment.
        """
        # 99999 is intentionally absent from DOBROPOST_STATUS_MAP.
        out = parse_list_shipment_response(
            {"content": [_row(123, "99999", "Some Brand New Status")]}
        )
        assert out == {}

    def test_known_status_id_still_produces_event(self) -> None:
        # "1" → DOBROPOST_STATUS_MAP['1'] = TrackingStatus.CREATED.
        out = parse_list_shipment_response(
            {"content": [_row(456, "1", "Ожидается на складе")]}
        )
        assert "456" in out
        events = out["456"]
        assert len(events) == 1
        assert events[0].provider_status_code == "1"

    def test_mixed_known_and_unknown(self) -> None:
        out = parse_list_shipment_response(
            {
                "content": [
                    _row(1, "1", "Ожидается на складе"),
                    _row(2, "99999", "Unknown"),
                    _row(3, "2", "Получен от курьера"),
                ]
            }
        )
        # Two known, one unknown skipped.
        assert set(out.keys()) == {"1", "3"}
