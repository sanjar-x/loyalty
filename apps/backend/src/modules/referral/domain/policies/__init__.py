"""Pure-function policies that drive referral economics.

* :mod:`programme_policy` — single immutable bag of every tunable
  parameter (welcome amount, tier thresholds, caps, hold days, fraud
  thresholds) loaded from settings at container assembly.
* :mod:`tier_policy` — derives :class:`CustomerTier` from lifetime
  activations and earnings.
* :mod:`reward_policy` — computes per-tier bonus and lifetime-share
  amounts, including the Telegram Premium multiplier.
* :mod:`caps_policy` — checks per-day / per-month / per-amount caps.
"""

from src.modules.referral.domain.policies.caps_policy import (
    CapDecision,
    CapsPolicy,
    CapVerdict,
)
from src.modules.referral.domain.policies.programme_policy import (
    ReferralProgrammePolicy,
)
from src.modules.referral.domain.policies.reward_policy import RewardPolicy
from src.modules.referral.domain.policies.tier_policy import TierPolicy

__all__ = [
    "CapDecision",
    "CapVerdict",
    "CapsPolicy",
    "ReferralProgrammePolicy",
    "RewardPolicy",
    "TierPolicy",
]
