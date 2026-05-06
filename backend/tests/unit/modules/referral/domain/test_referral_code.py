"""Unit tests for the :class:`ReferralCode` aggregate."""

from __future__ import annotations

import uuid

import pytest

from src.modules.referral.domain.aggregates import ReferralCode

pytestmark = pytest.mark.unit


class TestReferralCodeIssue:
    def test_issue_persists_owner_and_code(self) -> None:
        customer_id = uuid.uuid4()
        code = ReferralCode.issue(customer_id=customer_id, code="ABCD1234")

        assert code.customer_id == customer_id
        assert code.code == "ABCD1234"
        assert code.is_revoked is False
        assert code.version == 1

    def test_issue_emits_issued_event(self) -> None:
        code = ReferralCode.issue(customer_id=uuid.uuid4(), code="XYZ12345")
        events = code.domain_events

        assert len(events) == 1
        assert events[0].event_type == "ReferralCodeIssuedEvent"
        assert events[0].aggregate_type == "ReferralCode"
        assert events[0].aggregate_id == str(code.id)


class TestReferralCodeRevoke:
    def test_revoke_flips_flag_and_records_reason(self) -> None:
        code = ReferralCode.issue(customer_id=uuid.uuid4(), code="ABCDEFGH")
        code.revoke(reason="abuse")

        assert code.is_revoked is True
        assert code.revocation_reason == "abuse"
        assert code.revoked_at is not None
        assert code.version == 2

    def test_revoke_is_idempotent(self) -> None:
        code = ReferralCode.issue(customer_id=uuid.uuid4(), code="ABCDEFGH")
        code.revoke(reason="abuse")
        code.revoke(reason="another")

        # Status flag and version do not advance on the second call.
        assert code.is_revoked is True
        assert code.revocation_reason == "abuse"
        assert code.version == 2

    def test_revoke_emits_event_on_first_call_only(self) -> None:
        code = ReferralCode.issue(customer_id=uuid.uuid4(), code="ABCDEFGH")
        code.revoke(reason="abuse")
        code.revoke(reason="abuse")

        revoke_events = [
            e for e in code.domain_events if e.event_type == "ReferralCodeRevokedEvent"
        ]
        assert len(revoke_events) == 1
