"""Referral aggregate FSM states.

A ``Referral`` traverses the graph

::

    CREATED ─┬─→ PENDING_REVIEW ─┬─→ ACTIVATED ──→ REWARDED ──→ CANCELLED
             │                   │
             ├─→ ACTIVATED ──→ REWARDED ──→ CANCELLED
             ├─→ FRAUD_BLOCKED (terminal)
             ├─→ EXPIRED (terminal)
             └─→ CANCELLED (terminal)

``PENDING_REVIEW`` is an explicit state for the manual-review queue
(fraud score 60–79) — the FRD originally modelled it as a flag, but
making it a state keeps the FSM honest and lets the existing
:class:`StateMachineMixin` enforce transitions instead of scattering
``if`` checks across handlers.
"""

from __future__ import annotations

from enum import StrEnum


class ReferralStatus(StrEnum):
    CREATED = "created"
    PENDING_REVIEW = "pending_review"
    ACTIVATED = "activated"
    REWARDED = "rewarded"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FRAUD_BLOCKED = "fraud_blocked"
