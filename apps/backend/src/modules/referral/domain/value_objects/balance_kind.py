"""Loyalty-account balance kinds.

The shared :class:`Balance` aggregate is generic over a kind enum;
this module declares the loyalty-specific buckets:

* ``AVAILABLE`` — points the customer can spend on the next checkout.
* ``PENDING`` — points awaiting the 14-day pending-hold (or first-
  delivery, for invitee welcome bonuses) before they release into
  ``AVAILABLE``. Allowed to go negative when a refund clawback exceeds
  the available balance (FRD §3.5, ADR-006 §5).
* ``LIFETIME`` — monotonically-increasing total of every credit the
  customer has ever received. Used for tier evaluation and audit.
"""

from __future__ import annotations

from enum import StrEnum


class LoyaltyBalanceKind(StrEnum):
    """Per-bucket balance discriminator on a :class:`CustomerLoyalty` account."""

    AVAILABLE = "available"
    PENDING = "pending"
    LIFETIME = "lifetime"
