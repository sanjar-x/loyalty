"""CustomerLoyalty aggregate — multi-bucket wallet + tier.

Wraps the generic shared :class:`Account` so the loyalty domain owns
three things the kernel cannot:

1. The ``LoyaltyBalanceKind`` discriminator (AVAILABLE / PENDING /
   LIFETIME).
2. The ``allow_negative={PENDING}`` policy on construction (FRD §3.5,
   ADR-006 §5).
3. The customer's :class:`CustomerTier`, advanced eagerly on each
   activation by the application handler.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import attrs

from src.modules.referral.domain.events import CustomerTierUpgradedEvent
from src.modules.referral.domain.value_objects import (
    CustomerTier,
    LoyaltyBalanceKind,
)
from shared.interfaces.entities import AggregateRoot
from shared.ledger import Account, Balance


def _new_id() -> uuid.UUID:
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


@attrs.define
class CustomerLoyalty(AggregateRoot):
    """A customer's loyalty wallet + tier.

    The aggregate owns its underlying :class:`Account` so that ledger
    posts and tier upgrades are part of one transactional boundary.
    """

    id: uuid.UUID
    customer_id: uuid.UUID
    account: Account[LoyaltyBalanceKind]
    tier: CustomerTier
    lifetime_activations: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls, *, customer_id: uuid.UUID, currency: str = "RUB"
    ) -> CustomerLoyalty:
        now = datetime.now(UTC)
        balance = Balance.empty(
            kinds=LoyaltyBalanceKind,
            allow_negative=frozenset({LoyaltyBalanceKind.PENDING}),
        )
        account = Account[LoyaltyBalanceKind](
            id=_new_id(),
            owner_type="customer",
            owner_id=customer_id,
            currency=currency,
            balance=balance,
            created_at=now,
            updated_at=now,
        )
        return cls(
            id=account.id,
            customer_id=customer_id,
            account=account,
            tier=CustomerTier.BRONZE,
            lifetime_activations=0,
            created_at=now,
            updated_at=now,
        )

    # ------------------------------------------------------------------
    # Read accessors
    # ------------------------------------------------------------------

    @property
    def available_kopecks(self) -> int:
        return self.account.amount(LoyaltyBalanceKind.AVAILABLE)

    @property
    def pending_kopecks(self) -> int:
        return self.account.amount(LoyaltyBalanceKind.PENDING)

    @property
    def lifetime_kopecks(self) -> int:
        return self.account.amount(LoyaltyBalanceKind.LIFETIME)

    # ------------------------------------------------------------------
    # Tier evaluation
    # ------------------------------------------------------------------

    def upgrade_tier_to(self, target: CustomerTier) -> None:
        """Eagerly bump the tier; emits an event when the value changes.

        Down-grades are silently ignored (BR-rule 4 in the BRD).
        """
        from src.modules.referral.domain.policies.tier_policy import _TIER_ORDER

        if _TIER_ORDER[target] <= _TIER_ORDER[self.tier]:
            return
        previous = self.tier
        self.tier = target
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            CustomerTierUpgradedEvent(
                customer_id=self.customer_id,
                previous_tier=previous.value,
                new_tier=target.value,
            )
        )

    def increment_lifetime_activations(self) -> None:
        self.lifetime_activations += 1
        self.updated_at = datetime.now(UTC)
