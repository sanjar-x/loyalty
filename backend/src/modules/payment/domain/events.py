"""Payment domain events."""

import uuid
from dataclasses import dataclass

from src.shared.interfaces.entities import ModuleDomainEvent


@dataclass
class PaymentEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all payment domain events."""

    aggregate_type: str = "payment_intent"


@dataclass
class PaymentIntentInitiatedEvent(
    PaymentEvent,
    required_fields=("intent_id", "order_id"),
    aggregate_id_field="intent_id",
):
    intent_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    provider: str = ""
    amount: int = 0
    currency: str = ""
    event_type: str = "PaymentIntentInitiatedEvent"


@dataclass
class PaymentAuthorizedEvent(
    PaymentEvent,
    required_fields=("intent_id", "order_id"),
    aggregate_id_field="intent_id",
):
    intent_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    provider_reference: str = ""
    event_type: str = "PaymentAuthorizedEvent"


@dataclass
class PaymentCapturedEvent(
    PaymentEvent,
    required_fields=("intent_id", "order_id"),
    aggregate_id_field="intent_id",
):
    intent_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    provider_reference: str = ""
    captured_amount: int = 0
    currency: str = ""
    event_type: str = "PaymentCapturedEvent"


@dataclass
class PaymentFailedEvent(
    PaymentEvent,
    required_fields=("intent_id", "order_id"),
    aggregate_id_field="intent_id",
):
    intent_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    provider_reference: str = ""
    reason: str = ""
    event_type: str = "PaymentFailedEvent"


@dataclass
class PaymentRefundedEvent(
    PaymentEvent,
    required_fields=("intent_id", "order_id"),
    aggregate_id_field="intent_id",
):
    intent_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    refunded_amount: int = 0
    currency: str = ""
    event_type: str = "PaymentRefundedEvent"


@dataclass
class PaymentCancelledEvent(
    PaymentEvent,
    required_fields=("intent_id", "order_id"),
    aggregate_id_field="intent_id",
):
    intent_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    reason: str = ""
    event_type: str = "PaymentCancelledEvent"
