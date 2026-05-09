"""Unit tests for the Recipient aggregate."""

import uuid
from datetime import date

import pytest

from src.modules.recipient.domain.entities import Recipient
from src.modules.recipient.domain.exceptions import RecipientArchivedError
from src.modules.recipient.domain.value_objects import (
    CustomsData,
    Email,
    FullName,
    Phone,
    RecipientValidationStatus,
)

pytestmark = pytest.mark.unit


def _make() -> Recipient:
    return Recipient.create(
        identity_id=uuid.uuid4(),
        full_name=FullName(ru="Иван Иванов", lat="Ivan Ivanov"),
        phone=Phone(e164="+79108897762"),
        email=Email(value="user@example.com"),
        customs_data=CustomsData(
            passport_serial="1234",
            passport_number="567890",
            passport_issue_date=date(2015, 5, 22),
            birth_date=date(1990, 1, 1),
            inn="500100732272",
        ),
    )


class TestLifecycle:
    def test_create_emits_event(self) -> None:
        r = _make()
        assert r.validation_status == RecipientValidationStatus.PENDING
        assert any(e.event_type == "RecipientCreatedEvent" for e in r.domain_events)

    def test_mark_verified_idempotent(self) -> None:
        r = _make()
        r.mark_verified()
        assert r.validation_status == RecipientValidationStatus.VERIFIED
        events_before = len(r.domain_events)
        r.mark_verified()
        assert len(r.domain_events) == events_before

    def test_mark_invalid_records_reason(self) -> None:
        r = _make()
        r.mark_invalid(reason="DaData says no")
        assert r.validation_status == RecipientValidationStatus.INVALID
        assert r.validation_failed_reason == "DaData says no"

    def test_update_with_only_phone_keeps_validation_status(self) -> None:
        """REC-002 (D1.3) — non-customs edits (phone / email / full_name)
        leave the DobroPost validation result intact. DobroPost only
        validates passport + INN + birth_date; surfacing PENDING for a
        phone typo forces the customer to wait for a fresh DaData
        round-trip with no business reason."""
        r = _make()
        r.mark_verified()
        r.update(phone=Phone(e164="+79991234567"))
        assert r.validation_status == RecipientValidationStatus.VERIFIED

    def test_update_with_only_email_keeps_validation_status(self) -> None:
        from src.modules.recipient.domain.value_objects import Email

        r = _make()
        r.mark_verified()
        r.update(email=Email.parse("new@example.com"))
        assert r.validation_status == RecipientValidationStatus.VERIFIED

    def test_update_with_only_full_name_keeps_validation_status(self) -> None:
        from src.modules.recipient.domain.value_objects import FullName

        r = _make()
        r.mark_verified()
        r.update(
            full_name=FullName.parse(ru="Сергеев Андрей", lat="Sergeev Andrei"),
        )
        assert r.validation_status == RecipientValidationStatus.VERIFIED

    def test_update_with_customs_data_resets_validation_to_pending(self) -> None:
        """Customs-data edit (passport / INN / birth_date) must reset to
        PENDING — the previous DobroPost result no longer applies."""
        from datetime import date

        from src.modules.recipient.domain.value_objects import CustomsData

        r = _make()
        r.mark_verified()
        # Different valid INN — Recipient identity is fixed-checksum so we
        # can't just bump a digit; use a known-valid alternate INN instead.
        new_customs = CustomsData(
            passport_serial="9876",
            passport_number="543210",
            passport_issue_date=date(2015, 1, 1),
            birth_date=date(1990, 1, 1),
            inn="500100732272",
        )
        r.update(customs_data=new_customs)
        assert r.validation_status == RecipientValidationStatus.PENDING

    def test_archive_blocks_mutations(self) -> None:
        r = _make()
        r.archive()
        with pytest.raises(RecipientArchivedError):
            r.update(phone=Phone(e164="+79991234567"))
        with pytest.raises(RecipientArchivedError):
            r.mark_verified()

    def test_archive_idempotent(self) -> None:
        r = _make()
        r.archive()
        events_before = len(r.domain_events)
        r.archive()
        assert len(r.domain_events) == events_before
