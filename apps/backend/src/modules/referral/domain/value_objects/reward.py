"""Reward-related value objects.

* :class:`RewardKind` — discriminator that routes a :class:`ReferralReward`
  through the correct accrual / release path.
* :class:`RewardStatus` — FSM state of a single reward.
* :class:`RewardAmount` — typed integer amount in the smallest
  currency unit (kopecks for RUB), with non-negativity invariant.
"""

from __future__ import annotations

from enum import StrEnum

import attrs


class RewardKind(StrEnum):
    """Why this reward was issued.

    * ``INVITEE_WELCOME`` — the welcome bonus credited to the invitee
      at signup (pending until first delivered order).
    * ``REFERRER_BONUS`` — one-off credit to the referrer at activation
      (pending 14 days for refund window).
    * ``REFERRER_LIFETIME_SHARE`` — recurring percentage credit on each
      delivered order of the invitee, for 12 months after activation.
    """

    INVITEE_WELCOME = "invitee_welcome"
    REFERRER_BONUS = "referrer_bonus"
    REFERRER_LIFETIME_SHARE = "referrer_lifetime_share"


class RewardStatus(StrEnum):
    """Lifecycle state of a single :class:`ReferralReward`."""

    PENDING = "pending"
    RELEASED = "released"
    REVERSED = "reversed"
    EXPIRED = "expired"


@attrs.frozen
class RewardAmount:
    """Typed integer amount with the smallest currency unit (kopecks)."""

    kopecks: int
    currency: str = "RUB"

    def __attrs_post_init__(self) -> None:
        if self.kopecks < 0:
            raise ValueError(f"RewardAmount must be non-negative (got {self.kopecks})")
