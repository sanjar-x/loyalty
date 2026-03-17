# src/modules/identity/domain/events.py
"""
Domain events for the Identity module.

Events are emitted by aggregates, serialized via dataclasses.asdict(),
and persisted atomically with business data via Transactional Outbox.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.shared.interfaces.entities import DomainEvent


@dataclass
class IdentityRegisteredEvent(DomainEvent):
    """
    Identity registered (local auth).
    Consumer: user module → CreateUserConsumer (creates User row with Shared PK).
    """

    identity_id: uuid.UUID | None = None
    email: str = ""
    registered_at: datetime | None = None
    aggregate_type: str = "Identity"
    event_type: str = "IdentityRegisteredEvent"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if self.registered_at is None:
            self.registered_at = datetime.now(UTC)
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)


@dataclass
class IdentityDeactivatedEvent(DomainEvent):
    """
    Identity deactivated (all sessions revoked).
    Consumer: user module → AnonymizeUserConsumer (GDPR PII cleanup).
    """

    identity_id: uuid.UUID | None = None
    reason: str = ""
    deactivated_at: datetime | None = None
    aggregate_type: str = "Identity"
    event_type: str = "IdentityDeactivatedEvent"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if self.deactivated_at is None:
            self.deactivated_at = datetime.now(UTC)
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)


@dataclass
class RoleAssignmentChangedEvent(DomainEvent):
    """
    Role assigned or revoked for an identity.
    Consumer: cache invalidation (delete perms:{session_id} keys from Redis).
    """

    identity_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None
    action: str = ""  # "assigned" | "revoked"
    aggregate_type: str = "Identity"
    event_type: str = "RoleAssignmentChangedEvent"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if self.role_id is None:
            raise ValueError("role_id is required")
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)
