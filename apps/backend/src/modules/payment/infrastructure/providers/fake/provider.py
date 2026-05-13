"""Deterministic in-process payment provider for dev/test environments.

Two-step semantics (research (5) §3): authorize-only at checkout, capture
deferred until the manager procures the goods. ``auto_captured`` is
always ``False`` — there is no path that captures funds at order create
time. Capture happens later via ``capture()``.

Behaviour:

* ``authorize`` — succeeds for normal amounts; fails deterministically
  when ``amount % 100 == 13`` (test-only failure path).
* ``capture`` and ``refund`` — succeed unless the intent_id hex starts
  with ``"dead"`` (deterministic failure path for compensation tests).
"""

import uuid

from src.modules.payment.domain.exceptions import PaymentProviderError
from src.modules.payment.domain.interfaces import (
    IPaymentProvider,
    ProviderAuthorization,
    ProviderCapture,
    ProviderRefund,
)


class FakePaymentProvider(IPaymentProvider):
    PROVIDER_NAME = "fake"

    async def authorize(
        self,
        *,
        intent_id: uuid.UUID,
        amount: int,
        currency: str,
        idempotency_key: str,
        order_id: uuid.UUID,
    ) -> ProviderAuthorization:
        if amount % 100 == 13:
            raise PaymentProviderError(
                provider=self.PROVIDER_NAME,
                reason="DETERMINISTIC_AUTHORIZE_FAILURE",
            )
        return ProviderAuthorization(
            provider_reference=f"fake_{intent_id.hex}",
            client_secret=f"fake_secret_{intent_id.hex}",
            auto_captured=False,
        )

    async def capture(
        self,
        *,
        intent_id: uuid.UUID,
        provider_reference: str,
        idempotency_key: str,
    ) -> ProviderCapture:
        if intent_id.hex.startswith("dead"):
            raise PaymentProviderError(
                provider=self.PROVIDER_NAME,
                reason="DETERMINISTIC_CAPTURE_FAILURE",
            )
        return ProviderCapture(provider_reference=provider_reference)

    async def refund(
        self,
        *,
        intent_id: uuid.UUID,
        amount: int,
        provider_reference: str,
        idempotency_key: str,
    ) -> ProviderRefund:
        if intent_id.hex.startswith("dead"):
            raise PaymentProviderError(
                provider=self.PROVIDER_NAME,
                reason="DETERMINISTIC_REFUND_FAILURE",
            )
        return ProviderRefund(provider_reference=provider_reference)
