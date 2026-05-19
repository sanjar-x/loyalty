"""Unit tests for the Recipient aggregate (post-ADR-011: shipping only)."""

import uuid

import pytest

from src.modules.recipient.domain.entities import Recipient
from src.modules.recipient.domain.exceptions import RecipientArchivedError
from src.modules.recipient.domain.value_objects import Email, FullName, Phone

pytestmark = pytest.mark.unit


def _make() -> Recipient:
    return Recipient.create(
        identity_id=uuid.uuid4(),
        full_name=FullName(ru="Иван Иванов", lat="Ivan Ivanov"),
        phone=Phone(e164="+79108897762"),
        email=Email(value="user@example.com"),
    )


class TestLifecycle:
    def test_create_emits_event(self) -> None:
        r = _make()
        assert any(e.event_type == "RecipientCreatedEvent" for e in r.domain_events)
        assert r.is_archived is False

    def test_update_phone_emits_updated_event(self) -> None:
        r = _make()
        r.update(phone=Phone(e164="+79991234567"))
        assert any(e.event_type == "RecipientUpdatedEvent" for e in r.domain_events)
        assert r.phone.e164 == "+79991234567"

    def test_update_email_changes_value(self) -> None:
        r = _make()
        r.update(email=Email.parse("new@example.com"))
        assert r.email.value == "new@example.com"

    def test_update_full_name_changes_value(self) -> None:
        r = _make()
        r.update(full_name=FullName.parse(ru="Сергеев Андрей", lat="Sergeev Andrei"))
        assert r.full_name.ru == "Сергеев Андрей"
        assert r.full_name.lat == "Sergeev Andrei"

    def test_archive_blocks_mutations(self) -> None:
        r = _make()
        r.archive()
        assert r.is_archived is True
        with pytest.raises(RecipientArchivedError):
            r.update(phone=Phone(e164="+79991234567"))

    def test_archive_idempotent(self) -> None:
        r = _make()
        r.archive()
        events_before = len(r.domain_events)
        r.archive()
        assert len(r.domain_events) == events_before
