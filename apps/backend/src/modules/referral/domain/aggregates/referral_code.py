"""ReferralCode aggregate.

A ReferralCode is owned by exactly one Customer (1:1) and carries the
public 8-character string used in deep links and manual-redeem flows.
The string is immutable: revocation flips ``is_revoked`` so the
attribution path can short-circuit while preserving audit. Re-issue
is not permitted — a customer who needs a new code is treated as a
distinct case and never gets one programmatically.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import attrs

from src.modules.referral.domain.events import (
    ReferralCodeIssuedEvent,
    ReferralCodeRevokedEvent,
)
from shared.interfaces.entities import AggregateRoot


def _new_id() -> uuid.UUID:
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


@attrs.define
class ReferralCode(AggregateRoot):
    """Public referral code owned by a single Customer."""

    id: uuid.UUID
    customer_id: uuid.UUID
    code: str
    issued_at: datetime
    is_revoked: bool = False
    revoked_at: datetime | None = None
    revocation_reason: str | None = None
    version: int = 1

    @classmethod
    def issue(cls, *, customer_id: uuid.UUID, code: str) -> ReferralCode:
        now = datetime.now(UTC)
        instance = cls(
            id=_new_id(),
            customer_id=customer_id,
            code=code,
            issued_at=now,
        )
        instance.add_domain_event(
            ReferralCodeIssuedEvent(
                code_id=instance.id,
                customer_id=customer_id,
                code=code,
            )
        )
        return instance

    def revoke(self, *, reason: str) -> None:
        if self.is_revoked:
            return  # idempotent
        self.is_revoked = True
        self.revoked_at = datetime.now(UTC)
        self.revocation_reason = reason
        self.version += 1
        self.add_domain_event(
            ReferralCodeRevokedEvent(
                code_id=self.id,
                customer_id=self.customer_id,
                reason=reason,
            )
        )
