"""Passport domain events.

Aggregate-emitted facts published to the outbox on UoW.commit. Mirrors
the recipient module's event-naming style (PascalCase event_type ==
class name; ``aggregate_type='passport'``).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.shared.interfaces.entities import ModuleDomainEvent


@dataclass(frozen=True)
class PassportEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all passport-domain events."""

    aggregate_type: str = "passport"


@dataclass(frozen=True)
class PassportCreatedEvent(
    PassportEvent,
    required_fields=("passport_id", "identity_id"),
    aggregate_id_field="passport_id",
):
    passport_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    event_type: str = "PassportCreatedEvent"


@dataclass(frozen=True)
class PassportUpdatedEvent(
    PassportEvent,
    required_fields=("passport_id",),
    aggregate_id_field="passport_id",
):
    passport_id: uuid.UUID | None = None
    # True when the updated fields could invalidate the prior
    # DaData/DobroPost verification (customs identifiers changed).
    customs_data_changed: bool = False
    event_type: str = "PassportUpdatedEvent"


@dataclass(frozen=True)
class PassportVerifiedEvent(
    PassportEvent,
    required_fields=("passport_id",),
    aggregate_id_field="passport_id",
):
    passport_id: uuid.UUID | None = None
    event_type: str = "PassportVerifiedEvent"


@dataclass(frozen=True)
class PassportInvalidatedEvent(
    PassportEvent,
    required_fields=("passport_id",),
    aggregate_id_field="passport_id",
):
    passport_id: uuid.UUID | None = None
    reason: str = ""
    event_type: str = "PassportInvalidatedEvent"


@dataclass(frozen=True)
class PassportArchivedEvent(
    PassportEvent,
    required_fields=("passport_id",),
    aggregate_id_field="passport_id",
):
    passport_id: uuid.UUID | None = None
    event_type: str = "PassportArchivedEvent"
