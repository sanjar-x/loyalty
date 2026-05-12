"""
Payment domain ports.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from attrs import frozen

from src.modules.payment.domain.entities import PaymentIntent


@frozen
class ProviderAuthorization:
    """Result of a provider's ``authorize_or_capture`` call."""

    provider_reference: str
    client_secret: str | None
    auto_captured: bool


@frozen
class ProviderCapture:
    """Result of a provider's explicit capture call."""

    provider_reference: str


@frozen
class ProviderRefund:
    """Result of a provider's refund call."""

    provider_reference: str


class IPaymentIntentRepository(ABC):
    """Repository contract for the PaymentIntent aggregate."""

    @abstractmethod
    async def add(self, intent: PaymentIntent) -> PaymentIntent: ...

    @abstractmethod
    async def get(self, intent_id: uuid.UUID) -> PaymentIntent | None: ...

    @abstractmethod
    async def get_for_update(self, intent_id: uuid.UUID) -> PaymentIntent | None: ...

    @abstractmethod
    async def get_by_idempotency_key(self, key: str) -> PaymentIntent | None: ...

    @abstractmethod
    async def update(self, intent: PaymentIntent) -> PaymentIntent: ...

    @abstractmethod
    async def find_expired_authorized(
        self, *, now: datetime, limit: int = 100
    ) -> list[uuid.UUID]:
        """Return ids of intents in AUTHORIZED with elapsed ``auth_expires_at``.

        Used by the auth-expiry cron (B3) to fail expired holds before
        the provider rejects a stale capture. Caller must invoke
        :class:`FailPaymentIntentHandler` per id inside its own UoW so
        per-intent failures don't poison the batch.
        """


class IPaymentProvider(ABC):
    """Port for any payment provider (real or fake).

    Implementations:
    * ``FakePaymentProvider`` — deterministic stub used outside prod.
    * Real PSP adapters (YooKassa, СБП, Tinkoff) — added later behind
      this same port without touching the application layer.

    Operations are idempotent: ``idempotency_key`` is forwarded to the
    upstream provider and persisted in ``payment_idempotency_keys`` with
    a UNIQUE constraint so retries cannot double-charge.
    """

    @abstractmethod
    async def authorize(
        self,
        *,
        intent_id: uuid.UUID,
        amount: int,
        currency: str,
        idempotency_key: str,
        order_id: uuid.UUID,
    ) -> ProviderAuthorization: ...

    @abstractmethod
    async def capture(
        self,
        *,
        intent_id: uuid.UUID,
        provider_reference: str,
        idempotency_key: str,
    ) -> ProviderCapture: ...

    @abstractmethod
    async def refund(
        self,
        *,
        intent_id: uuid.UUID,
        amount: int,
        provider_reference: str,
        idempotency_key: str,
    ) -> ProviderRefund: ...
