"""
PaymentIntent aggregate.

A PaymentIntent represents one attempt to collect payment for an Order.
It owns its FSM and only the order_id link to Order — Order/Payment are
separate bounded contexts (research (5)).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import ClassVar

from attr import dataclass

from src.modules.payment.domain.events import (
    PaymentAuthorizedEvent,
    PaymentCancelledEvent,
    PaymentCapturedEvent,
    PaymentFailedEvent,
    PaymentIntentInitiatedEvent,
    PaymentRefundedEvent,
)
from src.modules.payment.domain.exceptions import (
    PaymentIntentAlreadyTerminalError,
    PaymentIntentInvalidTransitionError,
)
from src.modules.payment.domain.value_objects import (
    PaymentIntentStatus,
    ProviderCode,
)
from src.shared.interfaces.entities import AggregateRoot
from src.shared.interfaces.fsm import StateMachineMixin

TERMINAL_STATUSES: frozenset[PaymentIntentStatus] = frozenset(
    {
        PaymentIntentStatus.REFUNDED,
        PaymentIntentStatus.CANCELLED,
        PaymentIntentStatus.FAILED,
    }
)


@dataclass
class PaymentIntent(AggregateRoot, StateMachineMixin[PaymentIntentStatus]):
    """Payment intent aggregate.

    Attributes:
        id: Unique intent identifier.
        order_id: Order this intent collects payment for (1:1 active intent).
        provider: Provider code (fake/yookassa/sbp/tinkoff).
        amount: Amount to authorize/capture in kopecks.
        currency: ISO 4217 currency code.
        status: Current FSM state.
        provider_reference: Provider-side identifier (filled after authorize).
        client_secret: Stub-only token returned to the client to confirm payment.
        idempotency_key: Client-supplied key forwarded to the provider.
        failure_reason: Filled when transitioning to FAILED.
        created_at: Creation timestamp.
        updated_at: Last mutation timestamp.
        version: Optimistic locking counter.
    """

    _ALLOWED_TRANSITIONS: ClassVar[
        dict[PaymentIntentStatus, frozenset[PaymentIntentStatus]]
    ] = {
        PaymentIntentStatus.INITIATED: frozenset(
            {PaymentIntentStatus.AUTHORIZED, PaymentIntentStatus.FAILED}
        ),
        PaymentIntentStatus.AUTHORIZED: frozenset(
            {
                PaymentIntentStatus.CAPTURED,
                PaymentIntentStatus.CANCELLED,
                PaymentIntentStatus.FAILED,
            }
        ),
        PaymentIntentStatus.CAPTURED: frozenset({PaymentIntentStatus.REFUNDED}),
        PaymentIntentStatus.REFUNDED: frozenset(),
        PaymentIntentStatus.CANCELLED: frozenset(),
        PaymentIntentStatus.FAILED: frozenset(),
    }
    _TERMINAL_STATES: ClassVar[frozenset[PaymentIntentStatus]] = TERMINAL_STATUSES
    _invalid_transition_exc: ClassVar[type[Exception]] = (
        PaymentIntentInvalidTransitionError
    )
    _already_terminal_exc: ClassVar[type[Exception]] = PaymentIntentAlreadyTerminalError

    id: uuid.UUID
    order_id: uuid.UUID
    provider: ProviderCode
    amount: int
    currency: str
    status: PaymentIntentStatus
    provider_reference: str | None
    client_secret: str | None
    idempotency_key: str
    failure_reason: str | None
    auth_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def initiate(
        cls,
        *,
        order_id: uuid.UUID,
        provider: ProviderCode,
        amount: int,
        currency: str,
        idempotency_key: str,
    ) -> PaymentIntent:
        if amount <= 0:
            raise PaymentIntentInvalidTransitionError(
                current="<new>", target=PaymentIntentStatus.INITIATED.value
            )
        now = datetime.now(UTC)
        intent = cls(
            id=uuid.uuid4(),
            order_id=order_id,
            provider=provider,
            amount=amount,
            currency=currency,
            status=PaymentIntentStatus.INITIATED,
            provider_reference=None,
            client_secret=None,
            idempotency_key=idempotency_key,
            failure_reason=None,
            auth_expires_at=None,
            created_at=now,
            updated_at=now,
            version=0,
        )
        intent.add_domain_event(
            PaymentIntentInitiatedEvent(
                intent_id=intent.id,
                order_id=order_id,
                provider=provider.value,
                amount=amount,
                currency=currency,
            )
        )
        return intent

    def authorize(
        self,
        *,
        provider_reference: str,
        client_secret: str | None = None,
        auth_expires_at: datetime | None = None,
    ) -> None:
        self._transition(PaymentIntentStatus.AUTHORIZED)
        self.provider_reference = provider_reference
        if client_secret is not None:
            self.client_secret = client_secret
        self.auth_expires_at = auth_expires_at
        self.add_domain_event(
            PaymentAuthorizedEvent(
                intent_id=self.id,
                order_id=self.order_id,
                provider_reference=provider_reference,
            )
        )

    def is_auth_expired(self) -> bool:
        if self.status != PaymentIntentStatus.AUTHORIZED:
            return False
        if self.auth_expires_at is None:
            return False
        return datetime.now(UTC) >= self.auth_expires_at

    def capture(self) -> None:
        self._transition(PaymentIntentStatus.CAPTURED)
        self.add_domain_event(
            PaymentCapturedEvent(
                intent_id=self.id,
                order_id=self.order_id,
                provider_reference=self.provider_reference or "",
                captured_amount=self.amount,
                currency=self.currency,
            )
        )

    def refund(self) -> None:
        self._transition(PaymentIntentStatus.REFUNDED)
        self.add_domain_event(
            PaymentRefundedEvent(
                intent_id=self.id,
                order_id=self.order_id,
                refunded_amount=self.amount,
                currency=self.currency,
            )
        )

    def fail(self, *, reason: str) -> None:
        self._transition(PaymentIntentStatus.FAILED)
        self.failure_reason = reason
        self.add_domain_event(
            PaymentFailedEvent(
                intent_id=self.id,
                order_id=self.order_id,
                provider_reference=self.provider_reference or "",
                reason=reason,
            )
        )

    def cancel(self, *, reason: str = "") -> None:
        self._transition(PaymentIntentStatus.CANCELLED)
        self.add_domain_event(
            PaymentCancelledEvent(
                intent_id=self.id, order_id=self.order_id, reason=reason
            )
        )
