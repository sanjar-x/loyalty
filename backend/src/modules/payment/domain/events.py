"""Payment domain events."""

import uuid
from dataclasses import dataclass
from typing import ClassVar

from src.shared.interfaces.entities import DomainEvent


@dataclass
class PaymentEvent(DomainEvent):
    """Intermediate base for all payment domain events."""

    _required_fields: ClassVar[tuple[str, ...]] = ()
    _aggregate_id_field: ClassVar[str] = ""

    aggregate_type: str = "payment_intent"
    event_type: str = "PaymentEvent"

    def __init_subclass__(
        cls,
        *,
        required_fields: tuple[str, ...] | None = None,
        aggregate_id_field: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(**kwargs)
        if required_fields is not None:
            cls._required_fields = required_fields
        if aggregate_id_field is not None:
            cls._aggregate_id_field = aggregate_id_field
        if required_fields is not None and cls.event_type == "PaymentEvent":
            raise TypeError(
                f"{cls.__name__} must define its own 'event_type' "
                "(inherited default 'PaymentEvent' would misroute events)"
            )

    def __post_init__(self) -> None:
        cls_name = type(self).__name__
        for field_name in self._required_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required for {cls_name}")
        if not self.aggregate_id and self._aggregate_id_field:
            self.aggregate_id = str(getattr(self, self._aggregate_id_field))


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
