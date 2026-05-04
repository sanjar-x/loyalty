"""Unit tests for the PaymentIntent FSM."""

import uuid

import pytest

from src.modules.payment.domain.entities import PaymentIntent
from src.modules.payment.domain.exceptions import (
    PaymentIntentAlreadyTerminalError,
    PaymentIntentInvalidTransitionError,
)
from src.modules.payment.domain.value_objects import (
    PaymentIntentStatus,
    ProviderCode,
)

pytestmark = pytest.mark.unit


def _intent() -> PaymentIntent:
    return PaymentIntent.initiate(
        order_id=uuid.uuid4(),
        provider=ProviderCode.FAKE,
        amount=10_000,
        currency="RUB",
        idempotency_key="idemp-key-12345",
    )


class TestHappyPath:
    def test_full_lifecycle(self) -> None:
        intent = _intent()
        assert intent.status == PaymentIntentStatus.INITIATED

        intent.authorize(provider_reference="prov_ref_1", client_secret="cs_1")
        assert intent.status == PaymentIntentStatus.AUTHORIZED
        assert intent.provider_reference == "prov_ref_1"

        intent.capture()
        assert intent.status == PaymentIntentStatus.CAPTURED

        intent.refund()
        assert intent.status == PaymentIntentStatus.REFUNDED
        assert intent.is_terminal


class TestIllegalTransitions:
    def test_capture_without_authorize_raises(self) -> None:
        intent = _intent()
        with pytest.raises(PaymentIntentInvalidTransitionError):
            intent.capture()

    def test_refund_without_capture_raises(self) -> None:
        intent = _intent()
        intent.authorize(provider_reference="x", client_secret="cs")
        with pytest.raises(PaymentIntentInvalidTransitionError):
            intent.refund()

    def test_failed_intent_cannot_authorize(self) -> None:
        # FAILED is a terminal state, so any further transition surfaces
        # the dedicated AlreadyTerminal error (not the generic Invalid-
        # Transition one) to make log/triage diagnosis unambiguous.
        intent = _intent()
        intent.fail(reason="provider_rejected")
        with pytest.raises(PaymentIntentAlreadyTerminalError):
            intent.authorize(provider_reference="x", client_secret="cs")

    def test_invalid_amount_raises(self) -> None:
        with pytest.raises(PaymentIntentInvalidTransitionError):
            PaymentIntent.initiate(
                order_id=uuid.uuid4(),
                provider=ProviderCode.FAKE,
                amount=0,
                currency="RUB",
                idempotency_key="key-zero-amount",
            )


class TestEvents:
    def test_initiate_emits_initiated_event(self) -> None:
        intent = _intent()
        assert any(
            ev.event_type == "PaymentIntentInitiatedEvent"
            for ev in intent.domain_events
        )

    def test_capture_emits_captured_event(self) -> None:
        intent = _intent()
        intent.authorize(provider_reference="x", client_secret="y")
        intent.capture()
        assert any(
            ev.event_type == "PaymentCapturedEvent" for ev in intent.domain_events
        )

    def test_refund_emits_refunded_event(self) -> None:
        intent = _intent()
        intent.authorize(provider_reference="x", client_secret="y")
        intent.capture()
        intent.refund()
        assert any(
            ev.event_type == "PaymentRefundedEvent" for ev in intent.domain_events
        )
