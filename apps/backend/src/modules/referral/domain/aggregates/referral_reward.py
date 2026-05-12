"""ReferralReward aggregate.

A single reward credit. Three FSM transitions, terminal at REVERSED /
EXPIRED. Releases / reversals are driven by:

* the ``release_pending_rewards`` cron (PENDING → RELEASED),
* the ``OrderRefundedEvent`` consumer (PENDING / RELEASED → REVERSED),
* the ``expire_invitee_welcome`` cron (PENDING → EXPIRED).

The mirror :class:`LedgerTransaction` on the shared ledger is posted by
the application handler — this aggregate emits domain events so the
ledger adapter can react inside the same UoW.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import ClassVar

import attrs

from src.modules.referral.domain.events import (
    ReferralRewardAccruedEvent,
    ReferralRewardExpiredEvent,
    ReferralRewardReleasedEvent,
    ReferralRewardReversedEvent,
)
from src.modules.referral.domain.exceptions import RewardInvalidStateError
from src.modules.referral.domain.value_objects import RewardKind, RewardStatus
from shared.interfaces.entities import AggregateRoot
from shared.interfaces.fsm import StateMachineMixin

_TERMINAL: frozenset[RewardStatus] = frozenset(
    {RewardStatus.REVERSED, RewardStatus.EXPIRED}
)


def _new_id() -> uuid.UUID:
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


class _RewardAlreadyTerminalError(RewardInvalidStateError):
    def __init__(self, *, status: str) -> None:
        super().__init__(current=status, attempted="transition")


class _RewardInvalidTransitionError(RewardInvalidStateError):
    def __init__(self, *, current: str, target: str) -> None:
        super().__init__(current=current, attempted=f"transition_to_{target}")


@attrs.define
class ReferralReward(AggregateRoot, StateMachineMixin[RewardStatus]):
    """A single reward credit (welcome, bonus, or lifetime share)."""

    _ALLOWED_TRANSITIONS: ClassVar[dict[RewardStatus, frozenset[RewardStatus]]] = {
        RewardStatus.PENDING: frozenset(
            {
                RewardStatus.RELEASED,
                RewardStatus.REVERSED,
                RewardStatus.EXPIRED,
            }
        ),
        RewardStatus.RELEASED: frozenset({RewardStatus.REVERSED}),
        RewardStatus.REVERSED: frozenset(),
        RewardStatus.EXPIRED: frozenset(),
    }
    _TERMINAL_STATES: ClassVar[frozenset[RewardStatus]] = _TERMINAL
    _invalid_transition_exc: ClassVar[type[Exception]] = _RewardInvalidTransitionError
    _already_terminal_exc: ClassVar[type[Exception]] = _RewardAlreadyTerminalError

    id: uuid.UUID
    referral_id: uuid.UUID
    customer_id: uuid.UUID
    kind: RewardKind
    amount_kopecks: int
    currency: str
    status: RewardStatus
    pending_until: datetime
    released_at: datetime | None
    reversed_at: datetime | None
    reversal_reason: str | None
    source_order_id: uuid.UUID | None
    ledger_transaction_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def accrue(
        cls,
        *,
        referral_id: uuid.UUID,
        customer_id: uuid.UUID,
        kind: RewardKind,
        amount_kopecks: int,
        hold_days: int,
        source_order_id: uuid.UUID | None = None,
        currency: str = "RUB",
    ) -> ReferralReward:
        if amount_kopecks <= 0:
            raise ValueError(f"reward amount must be positive (got {amount_kopecks})")
        now = datetime.now(UTC)
        instance = cls(
            id=_new_id(),
            referral_id=referral_id,
            customer_id=customer_id,
            kind=kind,
            amount_kopecks=amount_kopecks,
            currency=currency,
            status=RewardStatus.PENDING,
            pending_until=now + timedelta(days=hold_days),
            released_at=None,
            reversed_at=None,
            reversal_reason=None,
            source_order_id=source_order_id,
            ledger_transaction_id=None,
            created_at=now,
            updated_at=now,
        )
        instance.add_domain_event(
            ReferralRewardAccruedEvent(
                reward_id=instance.id,
                customer_id=customer_id,
                referral_id=referral_id,
                kind=kind.value,
                amount_kopecks=amount_kopecks,
            )
        )
        return instance

    def release(self, *, ledger_transaction_id: uuid.UUID) -> None:
        self._transition(RewardStatus.RELEASED)
        self.released_at = self.updated_at
        self.ledger_transaction_id = ledger_transaction_id
        self.add_domain_event(
            ReferralRewardReleasedEvent(
                reward_id=self.id,
                customer_id=self.customer_id,
                amount_kopecks=self.amount_kopecks,
            )
        )

    def reverse(self, *, reason: str) -> None:
        previous = self.status
        if previous is RewardStatus.PENDING or previous is RewardStatus.RELEASED:
            self._transition(RewardStatus.REVERSED)
        else:
            return  # idempotent for terminal states
        self.reversed_at = self.updated_at
        self.reversal_reason = reason
        self.add_domain_event(
            ReferralRewardReversedEvent(
                reward_id=self.id,
                customer_id=self.customer_id,
                amount_kopecks=self.amount_kopecks,
                previous_status=previous.value,
                reason=reason,
            )
        )

    def expire(self) -> None:
        if self.status is RewardStatus.EXPIRED:
            return  # idempotent
        self._transition(RewardStatus.EXPIRED)
        self.add_domain_event(ReferralRewardExpiredEvent(reward_id=self.id))

    @property
    def is_due(self) -> bool:
        return (
            self.status is RewardStatus.PENDING
            and datetime.now(UTC) >= self.pending_until
        )
