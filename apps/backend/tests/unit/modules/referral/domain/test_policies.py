"""Unit tests for the pure-function policies."""

from __future__ import annotations

import pytest

from src.modules.referral.domain.policies import (
    CapsPolicy,
    CapVerdict,
    ReferralProgrammePolicy,
    RewardPolicy,
    TierPolicy,
)
from src.modules.referral.domain.value_objects import CustomerTier

pytestmark = pytest.mark.unit


@pytest.fixture()
def programme() -> ReferralProgrammePolicy:
    return ReferralProgrammePolicy()


class TestTierPolicy:
    def test_bronze_default(self, programme: ReferralProgrammePolicy) -> None:
        policy = TierPolicy(programme=programme)
        assert (
            policy.evaluate(lifetime_activations=0, lifetime_amount_kopecks=0)
            is CustomerTier.BRONZE
        )

    def test_silver_via_activations(self, programme: ReferralProgrammePolicy) -> None:
        policy = TierPolicy(programme=programme)
        assert (
            policy.evaluate(lifetime_activations=5, lifetime_amount_kopecks=0)
            is CustomerTier.SILVER
        )

    def test_gold_via_amount(self, programme: ReferralProgrammePolicy) -> None:
        policy = TierPolicy(programme=programme)
        assert (
            policy.evaluate(lifetime_activations=0, lifetime_amount_kopecks=500_000)
            is CustomerTier.GOLD
        )

    def test_either_threshold_qualifies(
        self, programme: ReferralProgrammePolicy
    ) -> None:
        policy = TierPolicy(programme=programme)
        # 4 activations + 1 000 ₽ → SILVER via amount.
        assert (
            policy.evaluate(lifetime_activations=4, lifetime_amount_kopecks=100_000)
            is CustomerTier.SILVER
        )

    def test_no_downgrade(self, programme: ReferralProgrammePolicy) -> None:
        policy = TierPolicy(programme=programme)
        result = policy.evaluate(
            lifetime_activations=0,
            lifetime_amount_kopecks=0,
            current_tier=CustomerTier.GOLD,
        )
        assert result is CustomerTier.GOLD


class TestRewardPolicy:
    def test_referrer_bonus_per_tier(self, programme: ReferralProgrammePolicy) -> None:
        policy = RewardPolicy(programme=programme)
        assert (
            policy.referrer_bonus_amount(tier=CustomerTier.BRONZE, is_premium=False)
            == 25_000
        )
        assert (
            policy.referrer_bonus_amount(tier=CustomerTier.GOLD, is_premium=False)
            == 60_000
        )

    def test_premium_multiplier_applies(
        self, programme: ReferralProgrammePolicy
    ) -> None:
        policy = RewardPolicy(programme=programme)
        boosted = policy.referrer_bonus_amount(
            tier=CustomerTier.BRONZE, is_premium=True
        )
        # 25 000 × 1.5 = 37 500
        assert boosted == 37_500

    def test_lifetime_share_rounds_half_up(
        self, programme: ReferralProgrammePolicy
    ) -> None:
        policy = RewardPolicy(programme=programme)
        # Bronze 3 % of 1 234 ₽ (123 400 kopecks) = 3 702 kopecks.
        amount = policy.lifetime_share_amount(
            tier=CustomerTier.BRONZE,
            order_total_kopecks=123_400,
            is_premium=False,
        )
        assert amount == 3_702


class TestCapsPolicy:
    def test_allow_when_below_all_thresholds(
        self, programme: ReferralProgrammePolicy
    ) -> None:
        decision = CapsPolicy(programme=programme).check(
            activations_today=0,
            activations_this_month=0,
            amount_this_month_kopecks=0,
            proposed_amount_kopecks=25_000,
        )
        assert decision.is_allow
        assert decision.daily_remaining == 5
        assert decision.monthly_activations_remaining == 30
        assert decision.monthly_amount_remaining_kopecks == 1_000_000

    def test_daily_cap(self, programme: ReferralProgrammePolicy) -> None:
        decision = CapsPolicy(programme=programme).check(
            activations_today=5,
            activations_this_month=10,
            amount_this_month_kopecks=0,
            proposed_amount_kopecks=25_000,
        )
        assert decision.verdict is CapVerdict.DAILY_CAP

    def test_monthly_amount_cap(self, programme: ReferralProgrammePolicy) -> None:
        decision = CapsPolicy(programme=programme).check(
            activations_today=0,
            activations_this_month=10,
            amount_this_month_kopecks=990_000,
            proposed_amount_kopecks=25_000,
        )
        assert decision.verdict is CapVerdict.MONTHLY_AMOUNT_CAP
