"""Customer tier value object.

Tiers (BRONZE / SILVER / GOLD) determine the bonus amount paid to the
referrer at activation and the percentage of the lifetime share. The
mapping itself lives in :mod:`src.modules.referral.domain.policies.tier_policy`
so that tier evaluation stays a pure function the domain owns.
"""

from __future__ import annotations

from enum import StrEnum


class CustomerTier(StrEnum):
    """Referrer rank derived from lifetime activation count + earnings."""

    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
