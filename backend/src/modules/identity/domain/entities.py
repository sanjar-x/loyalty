"""Domain entities for the Identity module.

Defines the core aggregates and entities: Identity (aggregate root), Session,
LocalCredentials, Role, Permission, and LinkedAccount. All entities are pure
domain objects implemented as attrs dataclasses with no infrastructure dependencies.
"""

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

from attr import dataclass

from src.modules.identity.domain.events import (
    IdentityDeactivatedEvent,
    IdentityReactivatedEvent,
    StaffInvitationAcceptedEvent,
    StaffInvitedEvent,
)
from src.modules.identity.domain.exceptions import (
    IdentityAlreadyActiveError,
    IdentityAlreadyDeactivatedError,
    IdentityDeactivatedError,
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationNotPendingError,
    InvitationRevokedError,
    RefreshTokenReuseError,
    SessionExpiredError,
    SessionRevokedError,
)
from src.modules.identity.domain.value_objects import AccountType, IdentityType, InvitationStatus
from src.shared.interfaces.entities import AggregateRoot


@dataclass
class Identity(AggregateRoot):
    """Aggregate root representing an authentication identity.

    An Identity is the central entity in the IAM bounded context. It can
    authenticate via local credentials (email/password) or external OIDC
    providers, and maintains an active/deactivated lifecycle.

    Attributes:
        id: Unique identifier (UUIDv7 when available, UUIDv4 fallback).
        type: Authentication method (LOCAL or OIDC).
        is_active: Whether this identity can currently authenticate.
        created_at: Timestamp when the identity was created.
        updated_at: Timestamp of the last modification.
    """

    id: uuid.UUID
    type: IdentityType
    account_type: AccountType
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deactivated_at: datetime | None = None
    deactivated_by: uuid.UUID | None = None
    token_version: int = 1

    @classmethod
    def register(
        cls,
        identity_type: IdentityType,
        account_type: AccountType = AccountType.CUSTOMER,
    ) -> Identity:
        """Create a new active identity with the given authentication type.

        Args:
            identity_type: The authentication method for this identity.
            account_type: The type of account (CUSTOMER or STAFF). Defaults to CUSTOMER.

        Returns:
            A new Identity instance in active state.
        """
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            type=identity_type,
            account_type=account_type,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def register_staff(cls, identity_type: IdentityType = IdentityType.LOCAL) -> Identity:
        """Create a new active staff identity.

        Args:
            identity_type: The authentication method. Defaults to LOCAL.

        Returns:
            A new Identity instance with account_type=STAFF.
        """
        return cls.register(identity_type, AccountType.STAFF)

    def deactivate(self, reason: str, deactivated_by: uuid.UUID | None = None) -> None:
        """Deactivate this identity, revoking all access.

        Args:
            reason: Human-readable reason for deactivation.
            deactivated_by: Identity ID of the admin who initiated the deactivation.
                None means self-deactivation.

        Raises:
            IdentityAlreadyDeactivatedError: If the identity is already deactivated.
        """
        if not self.is_active:
            raise IdentityAlreadyDeactivatedError()
        self.is_active = False
        self.deactivated_at = datetime.now(UTC)
        self.deactivated_by = deactivated_by
        self.updated_at = self.deactivated_at
        self.add_domain_event(
            IdentityDeactivatedEvent(
                identity_id=self.id,
                reason=reason,
                deactivated_by=deactivated_by,
                aggregate_id=str(self.id),
            )
        )

    def reactivate(self) -> None:
        """Reactivate a deactivated identity.

        Raises:
            IdentityAlreadyActiveError: If the identity is already active.
        """
        if self.is_active:
            raise IdentityAlreadyActiveError()
        self.is_active = True
        self.deactivated_at = None
        self.deactivated_by = None
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            IdentityReactivatedEvent(
                identity_id=self.id,
                aggregate_id=str(self.id),
            )
        )

    def ensure_active(self) -> None:
        """Verify that this identity is active.

        Raises:
            IdentityDeactivatedError: If the identity has been deactivated.
        """
        if not self.is_active:
            raise IdentityDeactivatedError()

    def bump_token_version(self) -> None:
        """Increment token version to invalidate all outstanding JWTs."""
        self.token_version += 1
        self.updated_at = datetime.now(UTC)


@dataclass
class LocalCredentials:
    """Owned entity holding local email and password credentials for an Identity.

    Attributes:
        identity_id: Foreign key to the owning Identity.
        email: Login email address (unique across the system).
        password_hash: Argon2id (or legacy Bcrypt) password hash.
        created_at: Timestamp when credentials were created.
        updated_at: Timestamp of the last credential update.
    """

    identity_id: uuid.UUID
    email: str
    password_hash: str
    created_at: datetime
    updated_at: datetime


@dataclass
class Session:
    """Authentication session with refresh token rotation and reuse detection.

    Sessions implement the refresh token rotation pattern: each token refresh
    replaces the stored hash. Presenting an already-rotated token triggers
    reuse detection, which should revoke all sessions for the identity.

    Attributes:
        id: Unique session identifier.
        identity_id: The identity that owns this session.
        refresh_token_hash: SHA-256 hash of the current opaque refresh token.
        ip_address: Client IP address at session creation.
        user_agent: Client User-Agent string at session creation.
        is_revoked: Whether this session has been explicitly revoked.
        created_at: Timestamp when the session was created.
        expires_at: Timestamp when the refresh token expires.
        activated_roles: Role IDs activated for this session (NIST RBAC).
    """

    id: uuid.UUID
    identity_id: uuid.UUID
    refresh_token_hash: str
    ip_address: str
    user_agent: str
    is_revoked: bool
    created_at: datetime
    expires_at: datetime
    activated_roles: tuple[uuid.UUID, ...]
    last_active_at: datetime
    idle_expires_at: datetime

    @classmethod
    def create(
        cls,
        identity_id: uuid.UUID,
        refresh_token: str,
        ip_address: str,
        user_agent: str,
        role_ids: list[uuid.UUID],
        expires_days: int = 30,
        idle_timeout_minutes: int = 30,
    ) -> Session:
        """Create a new session with a hashed refresh token.

        Args:
            identity_id: The identity that owns this session.
            refresh_token: Raw opaque refresh token (will be SHA-256 hashed).
            ip_address: Client IP address.
            user_agent: Client User-Agent header value.
            role_ids: Role IDs to activate for this session.
            expires_days: Number of days until the refresh token expires.
            idle_timeout_minutes: Minutes of inactivity before session expires.

        Returns:
            A new Session instance.
        """
        now = datetime.now(UTC)
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        return cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            identity_id=identity_id,
            refresh_token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            is_revoked=False,
            created_at=now,
            expires_at=now + timedelta(days=expires_days),
            activated_roles=tuple(role_ids),
            last_active_at=now,
            idle_expires_at=now + timedelta(minutes=idle_timeout_minutes),
        )

    def touch(self, idle_timeout_minutes: int) -> None:
        """Extend idle timeout on activity (refresh token use)."""
        now = datetime.now(UTC)
        self.last_active_at = now
        self.idle_expires_at = now + timedelta(minutes=idle_timeout_minutes)

    def revoke(self) -> None:
        """Mark this session as revoked."""
        self.is_revoked = True

    def is_expired(self) -> bool:
        """Check whether this session's refresh token has expired.

        Returns:
            True if the current time is at or past the expiry timestamp.
        """
        return datetime.now(UTC) >= self.expires_at

    def rotate_refresh_token(self, new_token: str) -> str:
        """Replace the stored refresh token hash with a new one.

        Args:
            new_token: The new raw opaque refresh token.

        Returns:
            The SHA-256 hex digest of the new token.
        """
        new_hash = hashlib.sha256(new_token.encode()).hexdigest()
        self.refresh_token_hash = new_hash
        return new_hash

    def verify_refresh_token(self, candidate: str) -> None:
        """Verify that a candidate token matches the stored hash.

        Uses constant-time comparison to prevent timing attacks.

        Args:
            candidate: The raw refresh token to verify.

        Raises:
            RefreshTokenReuseError: If the candidate does not match.
        """
        candidate_hash = hashlib.sha256(candidate.encode()).hexdigest()
        if not hmac.compare_digest(self.refresh_token_hash, candidate_hash):
            raise RefreshTokenReuseError()

    def ensure_valid(self) -> None:
        """Verify that this session is neither expired, idle-expired, nor revoked.

        Raises:
            SessionExpiredError: If the session has expired (absolute or idle).
            SessionRevokedError: If the session has been revoked.
        """
        if self.is_expired():
            raise SessionExpiredError()
        if datetime.now(UTC) >= self.idle_expires_at:
            raise SessionExpiredError()
        if self.is_revoked:
            raise SessionRevokedError()


@dataclass
class Role:
    """RBAC role definition.

    Attributes:
        id: Unique role identifier.
        name: Human-readable role name (unique).
        description: Optional role description.
        is_system: If True, this role cannot be modified or deleted.
        target_account_type: Which account type this role may be assigned to.
            None means the role is assignable to any account type.
    """

    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    target_account_type: AccountType | None = None


@dataclass
class Permission:
    """RBAC permission in 'resource:action' codename format.

    Attributes:
        id: Unique permission identifier.
        codename: Permission codename (e.g. "orders:read").
        resource: The resource portion of the codename.
        action: The action portion of the codename.
        description: Optional human-readable description.
    """

    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None = None


@dataclass
class LinkedAccount:
    """External provider account linked to an Identity."""

    id: uuid.UUID
    identity_id: uuid.UUID
    provider: str
    provider_sub_id: str
    provider_email: str | None
    email_verified: bool
    provider_metadata: dict
    created_at: datetime
    updated_at: datetime

    def update_metadata(self, new_metadata: dict) -> bool:
        """Update provider_metadata if changed. Returns True if updated."""
        if self.provider_metadata != new_metadata:
            self.provider_metadata = new_metadata
            self.updated_at = datetime.now(UTC)
            return True
        return False


@dataclass
class StaffInvitation(AggregateRoot):
    """Aggregate root representing a staff invitation.

    Lifecycle: PENDING -> ACCEPTED | EXPIRED | REVOKED.
    Token: CSPRNG 256 bits -> SHA-256 hash stored in DB.
    TTL: 72 hours (configurable).

    Attributes:
        id: Unique invitation identifier.
        email: Email of the invitee.
        token_hash: SHA-256 hash of the invite token.
        role_ids: Roles to assign upon acceptance.
        invited_by: Identity ID of the admin who sent the invitation.
        status: Current invitation lifecycle status.
        created_at: When the invitation was created.
        expires_at: When the invitation expires.
        accepted_at: When the invitation was accepted (None if not accepted).
        accepted_identity_id: Identity ID of the invitee (None if not accepted).
    """

    id: uuid.UUID
    email: str
    token_hash: str
    role_ids: list[uuid.UUID]
    invited_by: uuid.UUID
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
    accepted_identity_id: uuid.UUID | None = None

    @classmethod
    def create(
        cls,
        email: str,
        invited_by: uuid.UUID,
        role_ids: list[uuid.UUID],
        raw_token: str,
        ttl_hours: int = 72,
    ) -> StaffInvitation:
        """Create a new staff invitation.

        Args:
            email: Email of the invitee.
            invited_by: Identity ID of the inviting admin.
            role_ids: Roles to assign upon acceptance.
            raw_token: Raw CSPRNG token (will be SHA-256 hashed).
            ttl_hours: Hours until expiration (default 72).

        Returns:
            A new StaffInvitation in PENDING status.
        """
        now = datetime.now(UTC)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        invitation = cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            email=email,
            token_hash=token_hash,
            role_ids=list(role_ids),
            invited_by=invited_by,
            status=InvitationStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(hours=ttl_hours),
        )
        invitation.add_domain_event(
            StaffInvitedEvent(
                invitation_id=invitation.id,
                email=email,
                invited_by=invited_by,
                role_ids=list(role_ids),
                aggregate_id=str(invitation.id),
            )
        )
        return invitation

    def accept(self, identity_id: uuid.UUID) -> None:
        """Accept the invitation after Identity + StaffMember creation.

        Args:
            identity_id: The newly created Identity's UUID.

        Raises:
            InvitationAlreadyAcceptedError: If already accepted.
            InvitationRevokedError: If revoked.
            InvitationExpiredError: If expired.
        """
        if self.status != InvitationStatus.PENDING:
            if self.status == InvitationStatus.ACCEPTED:
                raise InvitationAlreadyAcceptedError()
            if self.status == InvitationStatus.REVOKED:
                raise InvitationRevokedError()
            raise InvitationExpiredError()
        now = datetime.now(UTC)
        if now > self.expires_at:
            raise InvitationExpiredError()
        self.status = InvitationStatus.ACCEPTED
        self.accepted_at = now
        self.accepted_identity_id = identity_id
        self.add_domain_event(
            StaffInvitationAcceptedEvent(
                invitation_id=self.id,
                identity_id=identity_id,
                email=self.email,
                aggregate_id=str(self.id),
            )
        )

    def revoke(self) -> None:
        """Revoke a pending invitation.

        Raises:
            InvitationNotPendingError: If not in PENDING status.
        """
        if self.status != InvitationStatus.PENDING:
            raise InvitationNotPendingError()
        self.status = InvitationStatus.REVOKED

    def is_expired(self) -> bool:
        """Check whether the invitation has expired."""
        return datetime.now(UTC) > self.expires_at

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """SHA-256 hash a raw token for DB lookup."""
        return hashlib.sha256(raw_token.encode()).hexdigest()
