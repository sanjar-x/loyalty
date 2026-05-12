"""Unit tests for the :class:`Referral` aggregate FSM."""

from __future__ import annotations

import uuid

import pytest

from src.modules.referral.domain.aggregates import Referral
from src.modules.referral.domain.events import ReferralCancelledEvent
from src.modules.referral.domain.exceptions import (
    ReferralAlreadyTerminalError,
    ReferralInvalidTransitionError,
    SelfReferralError,
)
from src.modules.referral.domain.value_objects import (
    AttributionContext,
    ReferralChannel,
    ReferralStatus,
)

pytestmark = pytest.mark.unit


def _attribution() -> AttributionContext:
    return AttributionContext(
        channel=ReferralChannel.TG_START_PARAM,
        chat_instance="chat-1",
        auth_date="1714824000",
        signup_ip="203.0.113.5",
        signup_user_agent="ua",
    )


def _referral(*, expiry_days: int = 60) -> Referral:
    return Referral.create(
        referrer_customer_id=uuid.uuid4(),
        invitee_customer_id=uuid.uuid4(),
        referral_code_id=uuid.uuid4(),
        attribution=_attribution(),
        expiry_days=expiry_days,
    )


class TestReferralFactory:
    def test_create_initialises_status_and_expiry(self) -> None:
        ref = _referral()
        assert ref.status is ReferralStatus.CREATED
        assert ref.activated_at is None
        assert ref.qualifying_order_id is None
        assert ref.expires_at > ref.created_at

    def test_self_referral_rejected(self) -> None:
        same = uuid.uuid4()
        with pytest.raises(SelfReferralError):
            Referral.create(
                referrer_customer_id=same,
                invitee_customer_id=same,
                referral_code_id=uuid.uuid4(),
                attribution=_attribution(),
                expiry_days=60,
            )

    def test_create_emits_referral_created_event(self) -> None:
        ref = _referral()
        events = [
            e for e in ref.domain_events if e.event_type == "ReferralCreatedEvent"
        ]
        assert len(events) == 1


class TestReferralFSM:
    def test_happy_path_to_rewarded(self) -> None:
        ref = _referral()
        ref.mark_activated(qualifying_order_id=uuid.uuid4(), fraud_score=10)
        assert ref.status is ReferralStatus.ACTIVATED
        ref.mark_rewarded()
        assert ref.status is ReferralStatus.REWARDED

    def test_pending_review_path(self) -> None:
        ref = _referral()
        ref.mark_pending_review(fraud_score=70)
        assert ref.status is ReferralStatus.PENDING_REVIEW
        assert ref.fraud_score == 70
        ref.mark_activated(qualifying_order_id=uuid.uuid4(), fraud_score=70)
        assert ref.status is ReferralStatus.ACTIVATED

    def test_fraud_block_terminal(self) -> None:
        ref = _referral()
        ref.mark_fraud_blocked(fraud_score=85, reason="auto_block")
        assert ref.status is ReferralStatus.FRAUD_BLOCKED
        with pytest.raises(ReferralAlreadyTerminalError):
            ref.mark_activated(qualifying_order_id=uuid.uuid4(), fraud_score=85)

    def test_invalid_transition_from_created_to_rewarded(self) -> None:
        ref = _referral()
        with pytest.raises(ReferralInvalidTransitionError):
            ref.mark_rewarded()

    def test_expiry_is_idempotent(self) -> None:
        ref = _referral()
        ref.mark_expired()
        ref.mark_expired()
        events = [
            e for e in ref.domain_events if e.event_type == "ReferralExpiredEvent"
        ]
        assert len(events) == 1

    def test_cancellation_emits_event_and_records_reason(self) -> None:
        ref = _referral()
        ref.mark_activated(qualifying_order_id=uuid.uuid4(), fraud_score=10)
        ref.mark_cancelled(reason="qualifying_order_refunded")
        assert ref.status is ReferralStatus.CANCELLED
        assert ref.cancellation_reason == "qualifying_order_refunded"
        cancellations = [
            e for e in ref.domain_events if isinstance(e, ReferralCancelledEvent)
        ]
        assert len(cancellations) == 1
        assert cancellations[0].reason == "qualifying_order_refunded"
