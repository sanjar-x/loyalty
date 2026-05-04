"""Unit tests for the :class:`CustomerLoyalty` aggregate."""

from __future__ import annotations

import uuid

import pytest

from src.modules.referral.domain.aggregates import CustomerLoyalty
from src.modules.referral.domain.value_objects import CustomerTier, LoyaltyBalanceKind
from src.shared.ledger import InsufficientBalanceError

pytestmark = pytest.mark.unit


def _account() -> CustomerLoyalty:
    return CustomerLoyalty.create(customer_id=uuid.uuid4())


class TestCustomerLoyaltyCreate:
    def test_starts_at_zero_and_bronze(self) -> None:
        account = _account()
        assert account.tier is CustomerTier.BRONZE
        assert account.lifetime_activations == 0
        assert account.available_kopecks == 0
        assert account.pending_kopecks == 0
        assert account.lifetime_kopecks == 0


class TestPendingNegativeAllowed:
    def test_pending_can_go_negative_for_clawback(self) -> None:
        account = _account()
        # Available is strict (allow_negative excludes it) — but PENDING
        # is opt-in negative, mirroring the clawback semantics in
        # FRD §3.5 / ADR-006 §5.
        account.account.balance.debit(LoyaltyBalanceKind.PENDING, 100)
        assert account.pending_kopecks == -100

    def test_available_strict(self) -> None:
        account = _account()
        with pytest.raises(InsufficientBalanceError):
            account.account.balance.debit(LoyaltyBalanceKind.AVAILABLE, 100)


class TestTierUpgrade:
    def test_upgrade_emits_event(self) -> None:
        account = _account()
        account.upgrade_tier_to(CustomerTier.SILVER)
        assert account.tier is CustomerTier.SILVER

        events = [
            e
            for e in account.domain_events
            if e.event_type == "CustomerTierUpgradedEvent"
        ]
        assert len(events) == 1
        assert events[0].previous_tier == "BRONZE"
        assert events[0].new_tier == "SILVER"

    def test_downgrade_silently_ignored(self) -> None:
        account = _account()
        account.upgrade_tier_to(CustomerTier.GOLD)
        account.upgrade_tier_to(CustomerTier.SILVER)
        assert account.tier is CustomerTier.GOLD

    def test_idempotent_same_tier(self) -> None:
        account = _account()
        account.upgrade_tier_to(CustomerTier.BRONZE)
        # No event emitted because the tier did not change.
        upgrades = [
            e
            for e in account.domain_events
            if e.event_type == "CustomerTierUpgradedEvent"
        ]
        assert upgrades == []
