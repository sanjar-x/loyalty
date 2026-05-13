"""Repository ports for the referral aggregates.

Each ``ReferralCode`` / ``Referral`` / ``ReferralReward`` /
``CustomerLoyalty`` aggregate has a dedicated repository — they are
loaded and persisted independently because their lifecycles do not
share transaction boundaries (one referral spawns many rewards over
time; one customer accumulates many referrals).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.modules.referral.domain.aggregates.customer_loyalty import (
        CustomerLoyalty,
    )
    from src.modules.referral.domain.aggregates.referral import Referral
    from src.modules.referral.domain.aggregates.referral_code import ReferralCode
    from src.modules.referral.domain.aggregates.referral_reward import (
        ReferralReward,
    )


class IReferralCodeRepository(Protocol):
    async def add(self, code: ReferralCode) -> ReferralCode: ...

    async def get(self, code_id: uuid.UUID) -> ReferralCode | None: ...

    async def get_by_customer(self, customer_id: uuid.UUID) -> ReferralCode | None: ...

    async def find_by_code(self, code: str) -> ReferralCode | None: ...

    async def update(self, code: ReferralCode) -> None: ...


class IReferralRepository(Protocol):
    async def add(self, referral: Referral) -> Referral: ...

    async def get(self, referral_id: uuid.UUID) -> Referral | None: ...

    async def get_for_update(self, referral_id: uuid.UUID) -> Referral | None: ...

    async def find_by_invitee(self, invitee_id: uuid.UUID) -> Referral | None: ...

    async def find_by_qualifying_order(
        self, order_id: uuid.UUID
    ) -> Referral | None: ...

    async def update(self, referral: Referral) -> None: ...

    async def list_for_admin(
        self,
        *,
        statuses: Sequence[str] | None,
        fraud_pending: bool | None,
        limit: int,
        cursor: datetime | None,
    ) -> list[Referral]: ...

    async def count_activations_today(self, referrer_id: uuid.UUID) -> int: ...

    async def count_activations_this_month(self, referrer_id: uuid.UUID) -> int: ...

    async def count_lifetime_activations(self, referrer_id: uuid.UUID) -> int: ...

    async def find_expired_pending(
        self, *, now: datetime, limit: int
    ) -> list[Referral]: ...


class IReferralRewardRepository(Protocol):
    async def add(self, reward: ReferralReward) -> ReferralReward: ...

    async def get_for_update(self, reward_id: uuid.UUID) -> ReferralReward | None: ...

    async def update(self, reward: ReferralReward) -> None: ...

    async def find_by_referral(
        self, referral_id: uuid.UUID
    ) -> list[ReferralReward]: ...

    async def find_by_source_order(
        self, order_id: uuid.UUID
    ) -> list[ReferralReward]: ...

    async def list_pending_due(
        self, *, due_before: datetime, limit: int
    ) -> list[ReferralReward]: ...

    async def sum_amount_this_month(self, customer_id: uuid.UUID) -> int: ...


class ICustomerLoyaltyRepository(Protocol):
    async def add(self, account: CustomerLoyalty) -> CustomerLoyalty: ...

    async def get_by_customer(
        self, customer_id: uuid.UUID
    ) -> CustomerLoyalty | None: ...

    async def get_for_update(
        self, customer_id: uuid.UUID
    ) -> CustomerLoyalty | None: ...

    async def update(self, account: CustomerLoyalty) -> None: ...
