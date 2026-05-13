"""Reward-amount calculation policy (pure functions).

Computes the kopecks payable for a given reward kind / tier / Premium
status / order total. Stays domain-pure: no I/O, no time, no
randomness — everything is derived from inputs and the immutable
:class:`ReferralProgrammePolicy`.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import attrs

from src.modules.referral.domain.policies.programme_policy import (
    ReferralProgrammePolicy,
)
from src.modules.referral.domain.value_objects import CustomerTier


@attrs.frozen
class RewardPolicy:
    programme: ReferralProgrammePolicy

    def invitee_welcome_amount(self, *, is_premium: bool) -> int:
        """Welcome bonus paid to the invitee at signup."""
        amount = self.programme.invitee_welcome_amount_kopecks
        return self._apply_premium(amount, is_premium=is_premium)

    def referrer_bonus_amount(self, *, tier: CustomerTier, is_premium: bool) -> int:
        """One-off bonus paid to the referrer at activation."""
        amount = self.programme.referrer_bonus_by_tier[tier]
        return self._apply_premium(amount, is_premium=is_premium)

    def lifetime_share_amount(
        self,
        *,
        tier: CustomerTier,
        order_total_kopecks: int,
        is_premium: bool,
    ) -> int:
        """Lifetime-share kopecks for one delivered invitee order."""
        pct = self.programme.lifetime_share_pct_by_tier[tier]
        raw = (Decimal(order_total_kopecks) * pct / Decimal(100)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return self._apply_premium(int(raw), is_premium=is_premium)

    def _apply_premium(self, amount: int, *, is_premium: bool) -> int:
        if not is_premium:
            return amount
        boosted = (Decimal(amount) * self.programme.premium_multiplier).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return int(boosted)
