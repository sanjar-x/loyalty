"""Immutable bag of every tunable referral-programme parameter.

Every policy lives behind one ``ReferralProgrammePolicy`` instance so
that changing the programme — for marketing campaigns, A/B tests, or
launch-day calibration — is a single-place edit. The instance is
loaded once at container assembly from :class:`Settings` defaults
declared in ``src.bootstrap.config``.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

import attrs

from src.modules.referral.domain.value_objects import CustomerTier


@attrs.frozen
class ReferralProgrammePolicy:
    """Single source of truth for every numeric programme parameter.

    Defaults follow [[BRD - Referral System]] BR-2 / BR-5 / BR-8.
    """

    # Reward amounts ---------------------------------------------------------
    invitee_welcome_amount_kopecks: int = 25_000  # 250 ₽
    referrer_bonus_by_tier: Mapping[CustomerTier, int] = attrs.field(
        factory=lambda: {
            CustomerTier.BRONZE: 25_000,  # 250 ₽
            CustomerTier.SILVER: 40_000,  # 400 ₽
            CustomerTier.GOLD: 60_000,  # 600 ₽
        }
    )
    lifetime_share_pct_by_tier: Mapping[CustomerTier, Decimal] = attrs.field(
        factory=lambda: {
            CustomerTier.BRONZE: Decimal("3.0"),
            CustomerTier.SILVER: Decimal("5.0"),
            CustomerTier.GOLD: Decimal("8.0"),
        }
    )
    premium_multiplier: Decimal = Decimal("1.5")

    # Tier thresholds (lifetime activations / lifetime amount kopecks) -------
    silver_min_activations: int = 5
    silver_min_amount_kopecks: int = 100_000  # 1 000 ₽
    gold_min_activations: int = 15
    gold_min_amount_kopecks: int = 500_000  # 5 000 ₽

    # Time windows -----------------------------------------------------------
    pending_hold_days: int = 14
    welcome_hold_days: int = 60
    referral_expiry_days: int = 60
    lifetime_share_window_days: int = 365

    # Caps -------------------------------------------------------------------
    monthly_activations_cap: int = 30
    daily_activations_cap: int = 5
    monthly_amount_cap_kopecks: int = 1_000_000  # 10 000 ₽
    min_qualifying_order_kopecks: int = 50_000  # 500 ₽

    # Anti-fraud thresholds --------------------------------------------------
    fraud_review_threshold: int = 60
    fraud_block_threshold: int = 80

    # Spend cap on checkout --------------------------------------------------
    spend_max_pct_of_order: Decimal = Decimal("20.0")

    # Code generation --------------------------------------------------------
    code_length: int = 8
    # Avoid visually-ambiguous characters (no O / 0 / I / 1 / L).
    code_alphabet: str = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
