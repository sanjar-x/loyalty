"""Pluggable fraud evaluator port + signal-bag :class:`FraudContext`.

The Phase-1 implementation is a heuristic over 7 weighted signals; a
future Phase-3 ML implementation will plug into the same contract.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Protocol

import attrs


class FraudVerdictKind(StrEnum):
    APPROVE = "approve"  # score < review_threshold
    REVIEW = "review"  # review_threshold ≤ score < block_threshold
    BLOCK = "block"  # score ≥ block_threshold


@attrs.frozen
class FraudVerdict:
    score: int
    verdict: FraudVerdictKind
    reasons: tuple[str, ...]


@attrs.frozen
class FraudContext:
    """Frozen bag of every signal a fraud rule may inspect.

    Attributes:
        referral_id: The referral being evaluated.
        referrer_id: Aggregate ID of the referrer's Customer.
        invitee_id: Aggregate ID of the invitee's Customer.
        qualifying_order_id: Invitee's first delivered order.
        qualifying_order_amount_kopecks: Total amount of that order.
        qualifying_order_created_at: When the order was placed.
        invitee_signup_at: When the invitee's identity was created.
        referrer_signup_ip / invitee_signup_ip: IPs captured at signup.
        referrer_user_agent / invitee_user_agent: UAs captured at signup.
        referrer_phone / invitee_phone: Normalised contact phones.
        referrer_activations_today: Sliding-window count for burst rate.
    """

    referral_id: uuid.UUID
    referrer_id: uuid.UUID
    invitee_id: uuid.UUID
    qualifying_order_id: uuid.UUID
    qualifying_order_amount_kopecks: int
    qualifying_order_created_at: datetime
    invitee_signup_at: datetime
    referrer_signup_ip: str | None
    invitee_signup_ip: str | None
    referrer_user_agent: str | None
    invitee_user_agent: str | None
    referrer_phone: str | None
    invitee_phone: str | None
    referrer_activations_today: int


class IFraudEvaluator(Protocol):
    async def evaluate(self, ctx: FraudContext) -> FraudVerdict: ...
