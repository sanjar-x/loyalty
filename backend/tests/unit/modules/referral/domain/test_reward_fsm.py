"""Unit tests for :class:`ReferralReward` FSM."""

from __future__ import annotations

import uuid

import pytest

from src.modules.referral.domain.aggregates import ReferralReward
from src.modules.referral.domain.exceptions import RewardInvalidStateError
from src.modules.referral.domain.value_objects import RewardKind, RewardStatus

pytestmark = pytest.mark.unit


def _reward(
    *,
    kind: RewardKind = RewardKind.REFERRER_BONUS,
    amount_kopecks: int = 25_000,
    hold_days: int = 14,
) -> ReferralReward:
    return ReferralReward.accrue(
        referral_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        kind=kind,
        amount_kopecks=amount_kopecks,
        hold_days=hold_days,
    )


class TestRewardAccrual:
    def test_amount_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            ReferralReward.accrue(
                referral_id=uuid.uuid4(),
                customer_id=uuid.uuid4(),
                kind=RewardKind.REFERRER_BONUS,
                amount_kopecks=0,
                hold_days=14,
            )

    def test_accrual_creates_pending_reward(self) -> None:
        reward = _reward()
        assert reward.status is RewardStatus.PENDING
        assert reward.amount_kopecks == 25_000
        assert reward.released_at is None

    def test_accrual_emits_event(self) -> None:
        reward = _reward()
        events = [
            e
            for e in reward.domain_events
            if e.event_type == "ReferralRewardAccruedEvent"
        ]
        assert len(events) == 1


class TestRewardFSM:
    def test_release_marks_status_and_records_ledger_id(self) -> None:
        reward = _reward()
        ledger_id = uuid.uuid4()
        reward.release(ledger_transaction_id=ledger_id)
        assert reward.status is RewardStatus.RELEASED
        assert reward.ledger_transaction_id == ledger_id
        assert reward.released_at is not None

    def test_reverse_from_pending(self) -> None:
        reward = _reward()
        reward.reverse(reason="qualifying_order_refunded")
        assert reward.status is RewardStatus.REVERSED
        assert reward.reversal_reason == "qualifying_order_refunded"

    def test_reverse_from_released(self) -> None:
        reward = _reward()
        reward.release(ledger_transaction_id=uuid.uuid4())
        reward.reverse(reason="lifetime_share_clawback")
        assert reward.status is RewardStatus.REVERSED

    def test_reverse_from_terminal_is_idempotent(self) -> None:
        reward = _reward()
        reward.expire()
        reward.reverse(reason="late")
        # Already EXPIRED; reverse() is a no-op.
        assert reward.status is RewardStatus.EXPIRED

    def test_release_after_terminal_raises(self) -> None:
        reward = _reward()
        reward.reverse(reason="r1")
        with pytest.raises(RewardInvalidStateError):
            reward.release(ledger_transaction_id=uuid.uuid4())
