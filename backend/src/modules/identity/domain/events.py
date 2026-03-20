"""Domain events for the Identity module.

Events are emitted by aggregates, serialized via ``dataclasses.asdict()``,
and persisted atomically with business data via the Transactional Outbox pattern.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.shared.interfaces.entities import DomainEvent


@dataclass
class IdentityRegisteredEvent(DomainEvent):
    """Emitted when a new identity is registered (local or OIDC).

    Consumed by the User module (``CreateUserConsumer``) to create a User row
    with a shared primary key.

    Attributes:
        identity_id: The newly registered identity's UUID.
        email: The email address used during registration.
        registered_at: Timestamp of registration (defaults to now).
        aggregate_type: Aggregate type identifier for outbox routing.
        event_type: Event type identifier for outbox routing.
    """

    identity_id: uuid.UUID | None = None
    email: str = ""
    registered_at: datetime | None = None
    account_type: str = "CUSTOMER"
    aggregate_type: str = "Identity"
    event_type: str = "identity_registered"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if self.registered_at is None:
            self.registered_at = datetime.now(UTC)
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)


@dataclass
class IdentityDeactivatedEvent(DomainEvent):
    """Emitted when an identity is deactivated (all sessions revoked).

    Consumed by the User module (``AnonymizeUserConsumer``) for GDPR PII cleanup.

    Attributes:
        identity_id: The deactivated identity's UUID.
        reason: Human-readable deactivation reason.
        deactivated_at: Timestamp of deactivation (defaults to now).
        aggregate_type: Aggregate type identifier for outbox routing.
        event_type: Event type identifier for outbox routing.
    """

    identity_id: uuid.UUID | None = None
    reason: str = ""
    deactivated_by: uuid.UUID | None = None
    deactivated_at: datetime | None = None
    aggregate_type: str = "Identity"
    event_type: str = "identity_deactivated"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if self.deactivated_at is None:
            self.deactivated_at = datetime.now(UTC)
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)


@dataclass
class RoleAssignmentChangedEvent(DomainEvent):
    """Emitted when a role is assigned to or revoked from an identity.

    Consumed by cache invalidation logic to delete ``perms:{session_id}``
    keys from Redis.

    Attributes:
        identity_id: The affected identity's UUID.
        role_id: The role that was assigned or revoked.
        action: Either "assigned" or "revoked".
        aggregate_type: Aggregate type identifier for outbox routing.
        event_type: Event type identifier for outbox routing.
    """

    identity_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None
    action: str = ""  # "assigned" | "revoked"
    aggregate_type: str = "Identity"
    event_type: str = "role_assignment_changed"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if self.role_id is None:
            raise ValueError("role_id is required")
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)


@dataclass
class IdentityReactivatedEvent(DomainEvent):
    """Emitted when an identity is reactivated by an admin.

    Attributes:
        identity_id: The reactivated identity's UUID.
        reactivated_at: Timestamp of reactivation (defaults to now).
        aggregate_type: Aggregate type identifier for outbox routing.
        event_type: Event type identifier for outbox routing.
    """

    identity_id: uuid.UUID | None = None
    reactivated_at: datetime | None = None
    aggregate_type: str = "Identity"
    event_type: str = "identity_reactivated"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if self.reactivated_at is None:
            self.reactivated_at = datetime.now(UTC)
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)


@dataclass
class StaffInvitedEvent(DomainEvent):
    """Emitted when a staff member is invited."""

    invitation_id: uuid.UUID | None = None
    email: str = ""
    invited_by: uuid.UUID | None = None
    role_ids: list[uuid.UUID] = field(default_factory=list)
    aggregate_type: str = "StaffInvitation"
    event_type: str = "staff_invited"

    def __post_init__(self) -> None:
        if not self.email:
            raise ValueError("email is required for StaffInvitedEvent")
        if not self.aggregate_id and self.invitation_id:
            self.aggregate_id = str(self.invitation_id)


@dataclass
class StaffInvitationAcceptedEvent(DomainEvent):
    """Emitted when a staff invitation is accepted."""

    invitation_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    email: str = ""
    aggregate_type: str = "StaffInvitation"
    event_type: str = "staff_invitation_accepted"

    def __post_init__(self) -> None:
        if not self.email:
            raise ValueError("email is required for StaffInvitationAcceptedEvent")
        if not self.aggregate_id and self.invitation_id:
            self.aggregate_id = str(self.invitation_id)


@dataclass
class TelegramIdentityCreatedEvent(DomainEvent):
    """Emitted when a new Identity is created via Telegram Mini App."""

    identity_id: uuid.UUID | None = None
    telegram_id: int = 0
    first_name: str = ""
    last_name: str = ""
    username: str | None = None
    start_param: str | None = None
    account_type: str = "CUSTOMER"
    aggregate_type: str = "Identity"
    event_type: str = "telegram_identity_created"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)
