"""Unit tests for the deterministic FakePaymentProvider."""

import uuid

import pytest

from src.modules.payment.domain.exceptions import PaymentProviderError
from src.modules.payment.infrastructure.providers.fake.provider import (
    FakePaymentProvider,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
class TestAuthorize:
    async def test_authorize_never_auto_captures(self) -> None:
        """Two-step semantics: capture is deferred to ``ProcureOrder``."""
        provider = FakePaymentProvider()
        result = await provider.authorize(
            intent_id=uuid.uuid4(),
            amount=10_000,
            currency="RUB",
            idempotency_key="k",
            order_id=uuid.uuid4(),
        )
        assert result.auto_captured is False
        assert result.client_secret is not None

    async def test_non_round_amount_does_not_auto_capture(self) -> None:
        provider = FakePaymentProvider()
        result = await provider.authorize(
            intent_id=uuid.uuid4(),
            amount=10_001,
            currency="RUB",
            idempotency_key="k",
            order_id=uuid.uuid4(),
        )
        assert result.auto_captured is False

    async def test_amount_mod100_eq_13_fails(self) -> None:
        provider = FakePaymentProvider()
        with pytest.raises(PaymentProviderError):
            await provider.authorize(
                intent_id=uuid.uuid4(),
                amount=113,
                currency="RUB",
                idempotency_key="k",
                order_id=uuid.uuid4(),
            )


@pytest.mark.asyncio
class TestCaptureAndRefund:
    async def test_capture_succeeds_for_normal_intent(self) -> None:
        provider = FakePaymentProvider()
        result = await provider.capture(
            intent_id=uuid.uuid4(),
            provider_reference="x",
            idempotency_key="k",
        )
        assert result.provider_reference == "x"

    async def test_capture_fails_for_dead_prefixed_intent(self) -> None:
        provider = FakePaymentProvider()
        # uuid hex starting with "dead"
        bad_id = uuid.UUID(hex="dead0000000000000000000000000001")
        with pytest.raises(PaymentProviderError):
            await provider.capture(
                intent_id=bad_id,
                provider_reference="x",
                idempotency_key="k",
            )

    async def test_refund_fails_for_dead_prefixed_intent(self) -> None:
        provider = FakePaymentProvider()
        bad_id = uuid.UUID(hex="dead0000000000000000000000000002")
        with pytest.raises(PaymentProviderError):
            await provider.refund(
                intent_id=bad_id,
                amount=100,
                provider_reference="x",
                idempotency_key="k",
            )
