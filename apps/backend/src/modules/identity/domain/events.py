"""Domain events for the Identity module.

Identity emits events from two distinct aggregate roots — ``Identity``
itself (registration, lifecycle, linked-account / role / token-version
changes) and ``StaffInvitation`` (the invite-accept hand-off). Concrete
events therefore override ``aggregate_type`` per event class on top of
:class:`IdentityEvent`, which only declares the placeholder default.

Validation and ``aggregate_id`` auto-fill come from
:class:`src.shared.interfaces.entities.ModuleDomainEvent`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.shared.interfaces.entities import ModuleDomainEvent


@dataclass(frozen=True)
class IdentityEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for events emitted by the identity bounded context.

    Identity has two aggregate roots (``Identity`` and ``StaffInvitation``);
    every concrete event MUST override ``aggregate_type`` with one of
    them — the default below is only a placeholder so that
    :class:`DomainEvent`'s integrity check passes for this abstract base.
    """

    aggregate_type: str = "Identity"

    def __init_subclass__(
        cls,
        *,
        abstract: bool = False,
        required_fields: tuple[str, ...] | None = None,
        aggregate_id_field: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(
            abstract=abstract,
            required_fields=required_fields,
            aggregate_id_field=aggregate_id_field,
            **kwargs,
        )
        if abstract or required_fields is None:
            return
        if "aggregate_type" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must override 'aggregate_type' — identity "
                "events span multiple aggregate kinds (Identity, "
                "StaffInvitation, ...) and cannot inherit the placeholder."
            )


# ---------------------------------------------------------------------------
# Identity aggregate events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityRegisteredEvent(
    IdentityEvent,
    required_fields=("identity_id",),
    aggregate_id_field="identity_id",
):
    """Emitted when a new identity is registered (local or OIDC).

    Consumed by the User module to provision a Customer or StaffMember
    profile sharing the identity's UUID.
    """

    identity_id: uuid.UUID | None = None
    email: str = ""
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    account_type: str = "CUSTOMER"
    username: str | None = None
    aggregate_type: str = "Identity"
    event_type: str = "IdentityRegisteredEvent"


@dataclass(frozen=True)
class IdentityDeactivatedEvent(
    IdentityEvent,
    required_fields=("identity_id",),
    aggregate_id_field="identity_id",
):
    """Emitted when an identity is deactivated; all sessions revoked.

    Consumed by the User module for GDPR-driven PII anonymisation of
    Customer profiles.
    """

    identity_id: uuid.UUID | None = None
    reason: str = ""
    deactivated_by: uuid.UUID | None = None
    deactivated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    aggregate_type: str = "Identity"
    event_type: str = "IdentityDeactivatedEvent"


@dataclass(frozen=True)
class IdentityReactivatedEvent(
    IdentityEvent,
    required_fields=("identity_id",),
    aggregate_id_field="identity_id",
):
    """Emitted when a deactivated identity is reactivated by an admin."""

    identity_id: uuid.UUID | None = None
    reactivated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    aggregate_type: str = "Identity"
    event_type: str = "IdentityReactivatedEvent"


@dataclass(frozen=True)
class RoleAssignmentChangedEvent(
    IdentityEvent,
    required_fields=("identity_id", "role_id"),
    aggregate_id_field="identity_id",
):
    """Emitted when a role is granted or revoked on an identity.

    Consumed by cache-invalidation logic to drop ``perms:{session_id}``
    keys from Redis so the next request rebuilds the permission set.
    """

    identity_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None
    action: str = ""  # "assigned" | "revoked"
    aggregate_type: str = "Identity"
    event_type: str = "RoleAssignmentChangedEvent"


@dataclass(frozen=True)
class LinkedAccountCreatedEvent(
    IdentityEvent,
    required_fields=("identity_id",),
    aggregate_id_field="identity_id",
):
    """Emitted when a new external provider is linked to an Identity.

    Triggered on Telegram Mini App / OIDC signup. Carries
    ``provider_metadata`` (Telegram ``is_premium``, locale, photo URL),
    ``start_param`` (deep-link payload), and the request-level
    ``signup_ip`` / ``signup_user_agent`` so downstream consumers
    (referral fraud-evaluator, login analytics, ...) can act without
    re-querying ``sessions``.
    """

    identity_id: uuid.UUID | None = None
    provider: str = ""
    provider_sub_id: str = ""
    provider_metadata: dict = field(default_factory=dict)
    start_param: str | None = None
    is_new_identity: bool = False
    signup_ip: str | None = None
    signup_user_agent: str | None = None
    aggregate_type: str = "Identity"
    event_type: str = "LinkedAccountCreatedEvent"


@dataclass(frozen=True)
class LinkedAccountRemovedEvent(
    IdentityEvent,
    required_fields=("identity_id",),
    aggregate_id_field="identity_id",
):
    """Emitted when an external provider link is removed."""

    identity_id: uuid.UUID | None = None
    provider: str = ""
    provider_sub_id: str = ""
    aggregate_type: str = "Identity"
    event_type: str = "LinkedAccountRemovedEvent"


@dataclass(frozen=True)
class IdentityTokenVersionBumpedEvent(
    IdentityEvent,
    required_fields=("identity_id",),
    aggregate_id_field="identity_id",
):
    """Emitted when ``token_version`` is bumped — invalidates all live JWTs."""

    identity_id: uuid.UUID | None = None
    new_version: int = 0
    reason: str = ""
    aggregate_type: str = "Identity"
    event_type: str = "IdentityTokenVersionBumpedEvent"


# ---------------------------------------------------------------------------
# StaffInvitation aggregate events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StaffInvitedEvent(
    IdentityEvent,
    required_fields=("invitation_id",),
    aggregate_id_field="invitation_id",
):
    """Emitted when an admin invites a new staff member."""

    invitation_id: uuid.UUID | None = None
    email: str = ""
    invited_by: uuid.UUID | None = None
    role_ids: list[uuid.UUID] = field(default_factory=list)
    aggregate_type: str = "StaffInvitation"
    event_type: str = "StaffInvitedEvent"


@dataclass(frozen=True)
class StaffInvitationAcceptedEvent(
    IdentityEvent,
    required_fields=("invitation_id",),
    aggregate_id_field="invitation_id",
):
    """Emitted when a staff invitation is accepted and the identity is linked."""

    invitation_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    email: str = ""
    aggregate_type: str = "StaffInvitation"
    event_type: str = "StaffInvitationAcceptedEvent"
