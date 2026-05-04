"""Tier evaluation — pure function from lifetime metrics → :class:`CustomerTier`.

Tier upgrades are eager (ADR-006 §7) — evaluated synchronously at
``ReferralActivatedEvent`` so that the bonus paid for the next
activation is calculated against the new tier without race windows.
Downgrades are forbidden by design.
"""

from __future__ import annotations

import attrs

from src.modules.referral.domain.policies.programme_policy import (
    ReferralProgrammePolicy,
)
from src.modules.referral.domain.value_objects import CustomerTier


@attrs.frozen
class TierPolicy:
    """Pure-function evaluator for :class:`CustomerTier`.

    Constructed once with a :class:`ReferralProgrammePolicy`; ``evaluate``
    takes the customer's lifetime metrics and returns the tier they
    qualify for. Treats the configured thresholds as inclusive lower
    bounds.
    """

    programme: ReferralProgrammePolicy

    def evaluate(
        self,
        *,
        lifetime_activations: int,
        lifetime_amount_kopecks: int,
        current_tier: CustomerTier = CustomerTier.BRONZE,
    ) -> CustomerTier:
        """Compute the tier matching ``lifetime_activations`` / amount.

        Either threshold qualifies (logical OR) — the BRD allows either
        an activation count or earnings total to bump the tier. The
        policy is monotonically-increasing: if ``current_tier`` is
        already higher than the threshold check would yield, the
        higher tier is returned.
        """
        if (
            lifetime_activations >= self.programme.gold_min_activations
            or lifetime_amount_kopecks >= self.programme.gold_min_amount_kopecks
        ):
            candidate = CustomerTier.GOLD
        elif (
            lifetime_activations >= self.programme.silver_min_activations
            or lifetime_amount_kopecks >= self.programme.silver_min_amount_kopecks
        ):
            candidate = CustomerTier.SILVER
        else:
            candidate = CustomerTier.BRONZE
        return _max_tier(current_tier, candidate)


_TIER_ORDER = {
    CustomerTier.BRONZE: 0,
    CustomerTier.SILVER: 1,
    CustomerTier.GOLD: 2,
}


def _max_tier(a: CustomerTier, b: CustomerTier) -> CustomerTier:
    return a if _TIER_ORDER[a] >= _TIER_ORDER[b] else b
