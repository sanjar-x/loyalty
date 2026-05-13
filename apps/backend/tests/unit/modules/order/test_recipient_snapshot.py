"""TYPE-005 — defense-in-depth validation on ``RecipientSnapshot``."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from src.modules.order.domain.recipient_snapshot import RecipientSnapshot


def _valid_kwargs() -> dict:
    return {
        "recipient_id": str(uuid.uuid4()),
        "full_name_ru": "Иванов Иван Иванович",
        "full_name_lat": "Ivanov Ivan Ivanovich",
        "phone": "+79001234567",
        "email": "ivanov@example.com",
        "passport_serial": "1234",
        "passport_number": "567890",
        "passport_issue_date": date(2020, 1, 1),
        "birth_date": date(1990, 1, 1),
        "inn": "123456789012",
    }


class TestRecipientSnapshotValidation:
    def test_happy_path(self) -> None:
        RecipientSnapshot(**_valid_kwargs())

    @pytest.mark.parametrize(
        "field, bad_value",
        [
            ("full_name_ru", ""),
            ("full_name_lat", "   "),
            ("phone", "12345"),  # too short
            ("phone", "not-a-phone"),
            ("email", "not-an-email"),
            ("email", "missing@tld"),
            ("passport_serial", "12345"),  # 5 digits
            ("passport_serial", "12a4"),  # non-digit
            ("passport_number", "12345"),  # 5 digits
            ("passport_number", "12345A"),
            ("inn", "1234567890"),  # 10 digits (legal entity, not allowed)
            ("inn", "12345678901a"),
        ],
    )
    def test_invalid_fields_rejected(self, field: str, bad_value: object) -> None:
        kwargs = _valid_kwargs()
        kwargs[field] = bad_value
        with pytest.raises(ValueError, match=field):
            RecipientSnapshot(**kwargs)

    def test_with_updated_data_revalidates(self) -> None:
        original_kwargs = _valid_kwargs()
        original = RecipientSnapshot(**original_kwargs)
        # ``recipient_id`` must match for the refresh to succeed; build
        # a fresh instance with updated phone but identical id.
        fresh_kwargs = _valid_kwargs()
        fresh_kwargs["recipient_id"] = original.recipient_id
        fresh_kwargs["phone"] = "+71234567890"
        fresh = RecipientSnapshot(**fresh_kwargs)
        replaced = original.with_updated_data(fresh=fresh)
        assert replaced.phone == "+71234567890"
        assert replaced.recipient_id == original.recipient_id

    def test_with_updated_data_rejects_different_recipient_id(self) -> None:
        original = RecipientSnapshot(**_valid_kwargs())
        fresh = RecipientSnapshot(**_valid_kwargs())  # different id
        with pytest.raises(ValueError, match="recipient_id"):
            original.with_updated_data(fresh=fresh)
