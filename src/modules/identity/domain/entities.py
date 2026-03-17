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

from src.modules.identity.domain.events import IdentityDeactivatedEvent
from src.modules.identity.domain.exceptions import (
    IdentityDeactivatedError,
    RefreshTokenReuseError,
    SessionExpiredError,
    SessionRevokedError,
)
from src.modules.identity.domain.value_objects import IdentityType
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
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def register(cls, identity_type: IdentityType) -> Identity:
        """Create a new active identity with the given authentication type.

        Args:
            identity_type: The authentication method for this identity.

        Returns:
            A new Identity instance in active state.
        """
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            type=identity_type,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def deactivate(self, reason: str) -> None:
        """Deactivate this identity and emit an IdentityDeactivatedEvent.

        Args:
            reason: Human-readable reason for deactivation (e.g. "user_request").
        """
        self.is_active = False
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            IdentityDeactivatedEvent(
                identity_id=self.id,
                reason=reason,
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
    activated_roles: list[uuid.UUID]

    @classmethod
    def create(
        cls,
        identity_id: uuid.UUID,
        refresh_token: str,
        ip_address: str,
        user_agent: str,
        role_ids: list[uuid.UUID],
        expires_days: int = 30,
    ) -> Session:
        """Create a new session with a hashed refresh token.

        Args:
            identity_id: The identity that owns this session.
            refresh_token: Raw opaque refresh token (will be SHA-256 hashed).
            ip_address: Client IP address.
            user_agent: Client User-Agent header value.
            role_ids: Role IDs to activate for this session.
            expires_days: Number of days until the refresh token expires.

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
            activated_roles=list(role_ids),
        )

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
        """Verify that this session is neither expired nor revoked.

        Raises:
            SessionExpiredError: If the session has expired.
            SessionRevokedError: If the session has been revoked.
        """
        if self.is_expired():
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
    """

    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool


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
    """External OIDC provider account linked to an Identity.

    Attributes:
        id: Unique linked account identifier.
        identity_id: The identity this external account is linked to.
        provider: OIDC provider name (e.g. "google", "github").
        provider_sub_id: The provider's unique subject identifier.
        provider_email: Email address reported by the provider, if available.
    """

    id: uuid.UUID
    identity_id: uuid.UUID
    provider: str
    provider_sub_id: str
    provider_email: str | None
