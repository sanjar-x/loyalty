"""Referral aggregate (FSM).

Represents the directed graph edge from a referrer to an invitee. The
edge is created when a valid ``start_param`` is observed at the
invitee's signup; it then traverses

::

    CREATED → PENDING_REVIEW → ACTIVATED → REWARDED
            ↘                ↘             ↘
              FRAUD_BLOCKED    CANCELLED     CANCELLED
              EXPIRED

States are owned by :class:`StateMachineMixin`; transition validation
is centralised so this aggregate can't drift from the FSM table.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import ClassVar

import attrs

from src.modules.referral.domain.events import (
    ReferralActivatedEvent,
    ReferralCancelledEvent,
    ReferralCreatedEvent,
    ReferralExpiredEvent,
    ReferralFraudBlockedEvent,
    ReferralPendingReviewEvent,
    ReferralRewardedEvent,
)
from src.modules.referral.domain.exceptions import (
    ReferralAlreadyTerminalError,
    ReferralInvalidTransitionError,
    SelfReferralError,
)
from src.modules.referral.domain.value_objects import (
    AttributionContext,
    ReferralStatus,
)
from shared.interfaces.entities import AggregateRoot
from shared.interfaces.fsm import StateMachineMixin

_TERMINAL: frozenset[ReferralStatus] = frozenset(
    {
        ReferralStatus.EXPIRED,
        ReferralStatus.CANCELLED,
        ReferralStatus.FRAUD_BLOCKED,
    }
)


def _new_id() -> uuid.UUID:
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


@attrs.define
class Referral(AggregateRoot, StateMachineMixin[ReferralStatus]):
    """Edge in the referrer → invitee graph with an FSM lifecycle."""

    _ALLOWED_TRANSITIONS: ClassVar[dict[ReferralStatus, frozenset[ReferralStatus]]] = {
        ReferralStatus.CREATED: frozenset(
            {
                ReferralStatus.ACTIVATED,
                ReferralStatus.PENDING_REVIEW,
                ReferralStatus.EXPIRED,
                ReferralStatus.CANCELLED,
                ReferralStatus.FRAUD_BLOCKED,
            }
        ),
        ReferralStatus.PENDING_REVIEW: frozenset(
            {
                ReferralStatus.ACTIVATED,
                ReferralStatus.FRAUD_BLOCKED,
                ReferralStatus.CANCELLED,
            }
        ),
        ReferralStatus.ACTIVATED: frozenset(
            {ReferralStatus.REWARDED, ReferralStatus.CANCELLED}
        ),
        ReferralStatus.REWARDED: frozenset({ReferralStatus.CANCELLED}),
        ReferralStatus.EXPIRED: frozenset(),
        ReferralStatus.CANCELLED: frozenset(),
        ReferralStatus.FRAUD_BLOCKED: frozenset(),
    }
    _TERMINAL_STATES: ClassVar[frozenset[ReferralStatus]] = _TERMINAL
    _invalid_transition_exc: ClassVar[type[Exception]] = ReferralInvalidTransitionError
    _already_terminal_exc: ClassVar[type[Exception]] = ReferralAlreadyTerminalError

    id: uuid.UUID
    referrer_customer_id: uuid.UUID
    invitee_customer_id: uuid.UUID
    referral_code_id: uuid.UUID
    attribution: AttributionContext
    status: ReferralStatus
    activated_at: datetime | None
    qualifying_order_id: uuid.UUID | None
    expires_at: datetime
    fraud_score: int
    fraud_reason: str | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
    version: int = 0

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        referrer_customer_id: uuid.UUID,
        invitee_customer_id: uuid.UUID,
        referral_code_id: uuid.UUID,
        attribution: AttributionContext,
        expiry_days: int,
    ) -> Referral:
        if referrer_customer_id == invitee_customer_id:
            raise SelfReferralError()
        now = datetime.now(UTC)
        instance = cls(
            id=_new_id(),
            referrer_customer_id=referrer_customer_id,
            invitee_customer_id=invitee_customer_id,
            referral_code_id=referral_code_id,
            attribution=attribution,
            status=ReferralStatus.CREATED,
            activated_at=None,
            qualifying_order_id=None,
            expires_at=now + timedelta(days=expiry_days),
            fraud_score=0,
            fraud_reason=None,
            cancellation_reason=None,
            created_at=now,
            updated_at=now,
        )
        instance.add_domain_event(
            ReferralCreatedEvent(
                referral_id=instance.id,
                referrer_customer_id=referrer_customer_id,
                invitee_customer_id=invitee_customer_id,
                source_channel=attribution.channel.value,
            )
        )
        return instance

    # ------------------------------------------------------------------
    # FSM mutations
    # ------------------------------------------------------------------

    def is_expired(self, *, now: datetime | None = None) -> bool:
        return (now or datetime.now(UTC)) >= self.expires_at

    def mark_pending_review(self, *, fraud_score: int) -> None:
        self._transition(ReferralStatus.PENDING_REVIEW)
        self.fraud_score = fraud_score
        self.add_domain_event(
            ReferralPendingReviewEvent(
                referral_id=self.id,
                fraud_score=fraud_score,
            )
        )

    def mark_activated(
        self,
        *,
        qualifying_order_id: uuid.UUID,
        fraud_score: int,
    ) -> None:
        self._transition(ReferralStatus.ACTIVATED)
        self.qualifying_order_id = qualifying_order_id
        self.activated_at = self.updated_at
        self.fraud_score = fraud_score
        self.add_domain_event(
            ReferralActivatedEvent(
                referral_id=self.id,
                referrer_customer_id=self.referrer_customer_id,
                invitee_customer_id=self.invitee_customer_id,
                qualifying_order_id=qualifying_order_id,
                fraud_score=fraud_score,
            )
        )

    def mark_rewarded(self) -> None:
        self._transition(ReferralStatus.REWARDED)
        self.add_domain_event(
            ReferralRewardedEvent(
                referral_id=self.id,
                referrer_customer_id=self.referrer_customer_id,
            )
        )

    def mark_expired(self) -> None:
        if self.status is ReferralStatus.EXPIRED:
            return  # idempotent
        self._transition(ReferralStatus.EXPIRED)
        self.add_domain_event(ReferralExpiredEvent(referral_id=self.id))

    def mark_cancelled(self, *, reason: str) -> None:
        self._transition(ReferralStatus.CANCELLED)
        self.cancellation_reason = reason
        self.add_domain_event(
            ReferralCancelledEvent(referral_id=self.id, reason=reason)
        )

    def mark_fraud_blocked(self, *, fraud_score: int, reason: str) -> None:
        self._transition(ReferralStatus.FRAUD_BLOCKED)
        self.fraud_score = fraud_score
        self.fraud_reason = reason
        self.add_domain_event(
            ReferralFraudBlockedEvent(
                referral_id=self.id,
                fraud_score=fraud_score,
                reason=reason,
            )
        )
