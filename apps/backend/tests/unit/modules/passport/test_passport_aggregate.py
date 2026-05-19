"""Unit tests for the Passport aggregate (ADR-011)."""

import uuid
from datetime import date

import pytest

from src.modules.passport.domain.entities import Passport
from src.modules.passport.domain.exceptions import PassportArchivedError
from src.modules.passport.domain.value_objects import (
    CustomsData,
    FullName,
    PassportValidationStatus,
)

pytestmark = pytest.mark.unit


def _make() -> Passport:
    return Passport.create(
        identity_id=uuid.uuid4(),
        full_name=FullName(ru="Иван Иванов", lat="Ivan Ivanov"),
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
        p = _make()
        assert p.validation_status == PassportValidationStatus.PENDING
        assert any(e.event_type == "PassportCreatedEvent" for e in p.domain_events)

    def test_mark_verified_idempotent(self) -> None:
        p = _make()
        p.mark_verified()
        assert p.validation_status == PassportValidationStatus.VERIFIED
        events_before = len(p.domain_events)
        p.mark_verified()
        assert len(p.domain_events) == events_before

    def test_mark_invalid_records_reason(self) -> None:
        p = _make()
        p.mark_invalid(reason="DaData says no")
        assert p.validation_status == PassportValidationStatus.INVALID
        assert p.validation_failed_reason == "DaData says no"

    def test_direct_validation_status_assignment_rejected(self) -> None:
        p = _make()
        with pytest.raises(AttributeError):
            p.validation_status = PassportValidationStatus.VERIFIED

    def test_update_full_name_only_keeps_validation_status(self) -> None:
        p = _make()
        p.mark_verified()
        p.update(full_name=FullName(ru="Сергеев Андрей", lat="Sergeev Andrei"))
        assert p.validation_status == PassportValidationStatus.VERIFIED

    def test_update_customs_data_resets_to_pending(self) -> None:
        p = _make()
        p.mark_verified()
        new_customs = CustomsData(
            passport_serial="9876",
            passport_number="543210",
            passport_issue_date=date(2015, 1, 1),
            birth_date=date(1990, 1, 1),
            inn="500100732272",
        )
        p.update(customs_data=new_customs)
        assert p.validation_status == PassportValidationStatus.PENDING

    def test_archive_blocks_mutations(self) -> None:
        p = _make()
        p.archive()
        with pytest.raises(PassportArchivedError):
            p.update(full_name=FullName(ru="Иной Иной", lat="Other Other"))
        with pytest.raises(PassportArchivedError):
            p.mark_verified()

    def test_archive_idempotent(self) -> None:
        p = _make()
        p.archive()
        events_before = len(p.domain_events)
        p.archive()
        assert len(p.domain_events) == events_before
