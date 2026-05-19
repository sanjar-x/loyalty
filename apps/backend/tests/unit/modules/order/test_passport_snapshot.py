"""TYPE-005 — defense-in-depth validation on ``PassportSnapshot``.

Counterpart to ``test_recipient_snapshot.py``. The frozen VO carries
the customs payload reconstructed at admin-tooling time from the
``orders.passport_snapshot`` JSONB column, so format invariants must
hold even when the original Passport row has been archived.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from src.modules.order.domain.recipient_snapshot import PassportSnapshot


def _valid_kwargs() -> dict:
    return {
        "passport_id": str(uuid.uuid4()),
        "full_name_ru": "Иванов Иван Иванович",
        "full_name_lat": "Ivanov Ivan Ivanovich",
        "passport_serial": "1234",
        "passport_number": "567890",
        "passport_issue_date": date(2020, 1, 1),
        "birth_date": date(1990, 1, 1),
        "inn": "500100732272",
        "validation_status": "pending",
    }


class TestPassportSnapshotValidation:
    def test_happy_path(self) -> None:
        PassportSnapshot(**_valid_kwargs())

    @pytest.mark.parametrize(
        "field, bad_value",
        [
            ("passport_serial", "12345"),
            ("passport_serial", "12a4"),
            ("passport_number", "12345"),
            ("passport_number", "12345A"),
            ("inn", "1234567890"),
            ("inn", "12345678901a"),
        ],
    )
    def test_invalid_fields_rejected(self, field: str, bad_value: object) -> None:
        kwargs = _valid_kwargs()
        kwargs[field] = bad_value
        with pytest.raises(ValueError, match=field):
            PassportSnapshot(**kwargs)
