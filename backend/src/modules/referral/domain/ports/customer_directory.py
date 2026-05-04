"""Anti-corruption read port over the user / identity bounded contexts.

The referral domain reads a small frozen snapshot of Customer state to
power tier evaluation, fraud heuristics, and notification metadata.
The shape of :class:`CustomerSnapshot` is owned by referral; the
infrastructure adapter translates user / identity ORM rows into it.
"""

from __future__ import annotations

import uuid
from typing import Protocol

import attrs


@attrs.frozen
class CustomerSnapshot:
    """Read-only projection of a Customer + linked Identity / signup.

    Attributes:
        customer_id: Shared PK with Identity.
        first_name: For display in admin / notifications.
        last_name: For display.
        phone: Contact phone, normalised to ``+E164`` if present.
        is_telegram_premium: Latest known Premium flag from the
            Telegram linked-account metadata.
        signup_ip: IP captured during the original Telegram / OIDC
            signup (LinkedAccountCreatedEvent payload).
        signup_user_agent: User agent captured during signup.
        signup_at: Timestamp of original signup.
    """

    customer_id: uuid.UUID
    first_name: str
    last_name: str
    phone: str | None
    is_telegram_premium: bool
    signup_ip: str | None
    signup_user_agent: str | None


class ICustomerDirectory(Protocol):
    async def get(self, customer_id: uuid.UUID) -> CustomerSnapshot | None: ...

    async def is_telegram_premium(self, customer_id: uuid.UUID) -> bool: ...
