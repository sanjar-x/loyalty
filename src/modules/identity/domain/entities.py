# src/modules/identity/domain/entities.py
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
    """Aggregate Root: authentication identity."""

    id: uuid.UUID
    type: IdentityType
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def register(cls, identity_type: IdentityType) -> Identity:
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            type=identity_type,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def deactivate(self, reason: str) -> None:
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
        if not self.is_active:
            raise IdentityDeactivatedError()


@dataclass
class LocalCredentials:
    """Owned entity: local email+password credentials for an Identity."""

    identity_id: uuid.UUID
    email: str
    password_hash: str
    created_at: datetime
    updated_at: datetime


@dataclass
class Session:
    """Session with refresh token rotation and reuse detection."""

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
        self.is_revoked = True

    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at

    def rotate_refresh_token(self, new_token: str) -> str:
        new_hash = hashlib.sha256(new_token.encode()).hexdigest()
        self.refresh_token_hash = new_hash
        return new_hash

    def verify_refresh_token(self, candidate: str) -> None:
        candidate_hash = hashlib.sha256(candidate.encode()).hexdigest()
        if not hmac.compare_digest(self.refresh_token_hash, candidate_hash):
            raise RefreshTokenReuseError()

    def ensure_valid(self) -> None:
        if self.is_expired():
            raise SessionExpiredError()
        if self.is_revoked:
            raise SessionRevokedError()


@dataclass
class Role:
    """RBAC role definition."""

    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool


@dataclass
class Permission:
    """RBAC permission in 'resource:action' format."""

    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None = None


@dataclass
class LinkedAccount:
    """External OIDC provider link."""

    id: uuid.UUID
    identity_id: uuid.UUID
    provider: str
    provider_sub_id: str
    provider_email: str | None
