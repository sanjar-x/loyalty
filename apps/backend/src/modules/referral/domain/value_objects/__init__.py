"""Value objects for the referral bounded context.

* :mod:`reward` — :class:`RewardKind` / :class:`RewardStatus` / :class:`RewardAmount`.
* :mod:`tier` — :class:`CustomerTier` and the (immutable) :class:`TierPolicy`.
* :mod:`attribution` — :class:`ReferralChannel` / :class:`AttributionContext`.
* :mod:`status` — :class:`ReferralStatus` (Referral aggregate FSM).
* :mod:`balance_kind` — :class:`LoyaltyBalanceKind` for the shared ledger.
"""

from src.modules.referral.domain.value_objects.attribution import (
    AttributionContext,
    ReferralChannel,
)
from src.modules.referral.domain.value_objects.balance_kind import LoyaltyBalanceKind
from src.modules.referral.domain.value_objects.reward import (
    RewardAmount,
    RewardKind,
    RewardStatus,
)
from src.modules.referral.domain.value_objects.status import ReferralStatus
from src.modules.referral.domain.value_objects.tier import CustomerTier

__all__ = [
    "AttributionContext",
    "CustomerTier",
    "LoyaltyBalanceKind",
    "ReferralChannel",
    "ReferralStatus",
    "RewardAmount",
    "RewardKind",
    "RewardStatus",
]
