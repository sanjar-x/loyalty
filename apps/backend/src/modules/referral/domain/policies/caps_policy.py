"""Caps enforcement (per-day / per-month activations + per-month rewards).

Returns a :class:`CapDecision` so handlers can route to ``activate`` /
``cap_throttled`` paths without re-reading thresholds.
"""

from __future__ import annotations

from enum import StrEnum

import attrs

from src.modules.referral.domain.policies.programme_policy import (
    ReferralProgrammePolicy,
)


class CapVerdict(StrEnum):
    ALLOW = "allow"
    DAILY_CAP = "daily_cap"
    MONTHLY_ACTIVATION_CAP = "monthly_activation_cap"
    MONTHLY_AMOUNT_CAP = "monthly_amount_cap"


@attrs.frozen
class CapDecision:
    """Outcome of a caps check.

    ``verdict`` is the discriminator; ``activations_remaining`` /
    ``amount_remaining_kopecks`` are exposed for UI / structured logs.
    """

    verdict: CapVerdict
    daily_remaining: int
    monthly_activations_remaining: int
    monthly_amount_remaining_kopecks: int

    @property
    def is_allow(self) -> bool:
        return self.verdict is CapVerdict.ALLOW


@attrs.frozen
class CapsPolicy:
    programme: ReferralProgrammePolicy

    def check(
        self,
        *,
        activations_today: int,
        activations_this_month: int,
        amount_this_month_kopecks: int,
        proposed_amount_kopecks: int,
    ) -> CapDecision:
        """Evaluate caps for the next would-be activation."""
        daily_remaining = max(
            0, self.programme.daily_activations_cap - activations_today
        )
        monthly_act_remaining = max(
            0, self.programme.monthly_activations_cap - activations_this_month
        )
        monthly_amt_remaining = max(
            0,
            self.programme.monthly_amount_cap_kopecks - amount_this_month_kopecks,
        )

        if daily_remaining <= 0:
            verdict = CapVerdict.DAILY_CAP
        elif monthly_act_remaining <= 0:
            verdict = CapVerdict.MONTHLY_ACTIVATION_CAP
        elif proposed_amount_kopecks > monthly_amt_remaining:
            verdict = CapVerdict.MONTHLY_AMOUNT_CAP
        else:
            verdict = CapVerdict.ALLOW

        return CapDecision(
            verdict=verdict,
            daily_remaining=daily_remaining,
            monthly_activations_remaining=monthly_act_remaining,
            monthly_amount_remaining_kopecks=monthly_amt_remaining,
        )
