"""Referral aggregate roots — one file per aggregate."""

from src.modules.referral.domain.aggregates.customer_loyalty import CustomerLoyalty
from src.modules.referral.domain.aggregates.referral import Referral
from src.modules.referral.domain.aggregates.referral_code import ReferralCode
from src.modules.referral.domain.aggregates.referral_reward import ReferralReward

__all__ = [
    "CustomerLoyalty",
    "Referral",
    "ReferralCode",
    "ReferralReward",
]
