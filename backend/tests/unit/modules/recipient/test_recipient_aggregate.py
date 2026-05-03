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

    def test_update_resets_validation_to_pending(self) -> None:
        r = _make()
        r.mark_verified()
        r.update(phone=Phone(e164="+79991234567"))
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
