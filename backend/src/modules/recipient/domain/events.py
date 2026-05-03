"""Recipient domain events."""

import uuid
from dataclasses import dataclass
from typing import ClassVar

from src.shared.interfaces.entities import DomainEvent


@dataclass
class RecipientEvent(DomainEvent):
    _required_fields: ClassVar[tuple[str, ...]] = ()
    _aggregate_id_field: ClassVar[str] = ""

    aggregate_type: str = "recipient"
    event_type: str = "RecipientEvent"

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
        if required_fields is not None and cls.event_type == "RecipientEvent":
            raise TypeError(f"{cls.__name__} must define its own 'event_type'")

    def __post_init__(self) -> None:
        cls_name = type(self).__name__
        for field_name in self._required_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required for {cls_name}")
        if not self.aggregate_id and self._aggregate_id_field:
            self.aggregate_id = str(getattr(self, self._aggregate_id_field))


@dataclass
class RecipientCreatedEvent(
    RecipientEvent,
    required_fields=("recipient_id", "identity_id"),
    aggregate_id_field="recipient_id",
):
    recipient_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    event_type: str = "RecipientCreatedEvent"


@dataclass
class RecipientUpdatedEvent(
    RecipientEvent,
    required_fields=("recipient_id",),
    aggregate_id_field="recipient_id",
):
    recipient_id: uuid.UUID | None = None
    customs_data_changed: bool = False
    event_type: str = "RecipientUpdatedEvent"


@dataclass
class RecipientVerifiedEvent(
    RecipientEvent,
    required_fields=("recipient_id",),
    aggregate_id_field="recipient_id",
):
    recipient_id: uuid.UUID | None = None
    event_type: str = "RecipientVerifiedEvent"


@dataclass
class RecipientInvalidatedEvent(
    RecipientEvent,
    required_fields=("recipient_id",),
    aggregate_id_field="recipient_id",
):
    recipient_id: uuid.UUID | None = None
    reason: str = ""
    event_type: str = "RecipientInvalidatedEvent"


@dataclass
class RecipientArchivedEvent(
    RecipientEvent,
    required_fields=("recipient_id",),
    aggregate_id_field="recipient_id",
):
    recipient_id: uuid.UUID | None = None
    event_type: str = "RecipientArchivedEvent"
