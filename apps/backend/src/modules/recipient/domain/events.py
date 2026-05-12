"""Recipient domain events."""

import uuid
from dataclasses import dataclass

from src.shared.interfaces.entities import ModuleDomainEvent


@dataclass(frozen=True)
class RecipientEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all recipient-domain events."""

    aggregate_type: str = "recipient"


@dataclass(frozen=True)
class RecipientCreatedEvent(
    RecipientEvent,
    required_fields=("recipient_id", "identity_id"),
    aggregate_id_field="recipient_id",
):
    recipient_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    event_type: str = "RecipientCreatedEvent"


@dataclass(frozen=True)
class RecipientUpdatedEvent(
    RecipientEvent,
    required_fields=("recipient_id",),
    aggregate_id_field="recipient_id",
):
    recipient_id: uuid.UUID | None = None
    customs_data_changed: bool = False
    event_type: str = "RecipientUpdatedEvent"


@dataclass(frozen=True)
class RecipientVerifiedEvent(
    RecipientEvent,
    required_fields=("recipient_id",),
    aggregate_id_field="recipient_id",
):
    recipient_id: uuid.UUID | None = None
    event_type: str = "RecipientVerifiedEvent"


@dataclass(frozen=True)
class RecipientInvalidatedEvent(
    RecipientEvent,
    required_fields=("recipient_id",),
    aggregate_id_field="recipient_id",
):
    recipient_id: uuid.UUID | None = None
    reason: str = ""
    event_type: str = "RecipientInvalidatedEvent"


@dataclass(frozen=True)
class RecipientArchivedEvent(
    RecipientEvent,
    required_fields=("recipient_id",),
    aggregate_id_field="recipient_id",
):
    recipient_id: uuid.UUID | None = None
    event_type: str = "RecipientArchivedEvent"
