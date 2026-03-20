# tests/factories/identity_mothers.py
"""Object Mothers for Identity module domain entities."""

import uuid
from datetime import UTC, datetime

from src.modules.identity.domain.entities import (
    Identity,
    LinkedAccount,
    LocalCredentials,
    Permission,
    Role,
    Session,
)
from src.modules.identity.domain.value_objects import PrimaryAuthMethod


class IdentityMothers:
    """Pre-built Identity aggregate configurations."""

    @staticmethod
    def active_local() -> Identity:
        """Standard active identity with LOCAL credentials."""
        return Identity.register(PrimaryAuthMethod.LOCAL)

    @staticmethod
    def active_oidc() -> Identity:
        """Standard active identity via OIDC provider."""
        return Identity.register(PrimaryAuthMethod.OIDC)

    @staticmethod
    def active_telegram() -> Identity:
        """Standard active identity via Telegram."""
        return Identity.register(PrimaryAuthMethod.TELEGRAM)

    @staticmethod
    def deactivated(reason: str = "test_deactivation") -> Identity:
        """Identity that has been deactivated — ensure_active() will raise."""
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        identity.deactivate(reason=reason)
        identity.clear_domain_events()
        return identity

    @staticmethod
    def with_credentials(
        email: str = "test@example.com",
        password_hash: str = "$argon2id$v=19$m=65536,t=3,p=4$test",
    ) -> tuple[Identity, LocalCredentials]:
        """Identity + LocalCredentials pair."""
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        creds = LocalCredentials(
            identity_id=identity.id,
            email=email,
            password_hash=password_hash,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return identity, creds

    @staticmethod
    def with_session(
        ip_address: str = "127.0.0.1",
        user_agent: str = "TestAgent/1.0",
    ) -> tuple[Identity, Session, str]:
        """Identity + active Session + raw refresh token."""
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        raw_token = f"refresh-{uuid.uuid4().hex}"
        session = Session.create(
            identity_id=identity.id,
            refresh_token=raw_token,
            ip_address=ip_address,
            user_agent=user_agent,
            role_ids=[],
            expires_days=30,
        )
        return identity, session, raw_token


class SessionMothers:
    """Pre-built Session configurations."""

    @staticmethod
    def active(identity_id: uuid.UUID | None = None) -> tuple[Session, str]:
        """Active, non-expired session + raw refresh token."""
        identity_id = identity_id or uuid.uuid4()
        raw_token = f"refresh-{uuid.uuid4().hex}"
        session = Session.create(
            identity_id=identity_id,
            refresh_token=raw_token,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        return session, raw_token

    @staticmethod
    def expired(identity_id: uuid.UUID | None = None) -> Session:
        """Expired session."""
        from datetime import timedelta

        identity_id = identity_id or uuid.uuid4()
        session = Session.create(
            identity_id=identity_id,
            refresh_token="expired-token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)
        return session

    @staticmethod
    def revoked(identity_id: uuid.UUID | None = None) -> Session:
        """Revoked session."""
        identity_id = identity_id or uuid.uuid4()
        session = Session.create(
            identity_id=identity_id,
            refresh_token="revoked-token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        session.revoke()
        return session


class RoleMothers:
    """Pre-built Role configurations."""

    @staticmethod
    def customer() -> Role:
        return Role(
            id=uuid.uuid4(),
            name="customer",
            description="Default customer role",
            is_system=False,
        )

    @staticmethod
    def admin() -> Role:
        return Role(
            id=uuid.uuid4(),
            name="admin",
            description="Administrator role",
            is_system=True,
        )

    @staticmethod
    def system_role(name: str = "system") -> Role:
        return Role(
            id=uuid.uuid4(),
            name=name,
            description=f"System role: {name}",
            is_system=True,
        )


class PermissionMothers:
    """Pre-built Permission configurations."""

    @staticmethod
    def brand_create() -> Permission:
        return Permission(
            id=uuid.uuid4(),
            codename="brands:create",
            resource="brands",
            action="create",
        )

    @staticmethod
    def brand_read() -> Permission:
        return Permission(
            id=uuid.uuid4(),
            codename="brands:read",
            resource="brands",
            action="read",
        )

    @staticmethod
    def category_manage() -> Permission:
        return Permission(
            id=uuid.uuid4(),
            codename="categories:manage",
            resource="categories",
            action="manage",
        )


class LinkedAccountMothers:
    """Pre-built LinkedAccount configurations."""

    @staticmethod
    def google(identity_id: uuid.UUID | None = None) -> LinkedAccount:
        now = datetime.now(UTC)
        return LinkedAccount(
            id=uuid.uuid4(),
            identity_id=identity_id or uuid.uuid4(),
            provider="google",
            provider_sub_id=f"google-{uuid.uuid4().hex[:8]}",
            provider_email="user@gmail.com",
            email_verified=True,
            provider_metadata={"name": "Test User", "picture": ""},
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def github(identity_id: uuid.UUID | None = None) -> LinkedAccount:
        now = datetime.now(UTC)
        return LinkedAccount(
            id=uuid.uuid4(),
            identity_id=identity_id or uuid.uuid4(),
            provider="github",
            provider_sub_id=f"github-{uuid.uuid4().hex[:8]}",
            provider_email="user@github.com",
            email_verified=True,
            provider_metadata={"name": "Test User", "picture": ""},
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def telegram(identity_id: uuid.UUID | None = None) -> LinkedAccount:
        now = datetime.now(UTC)
        return LinkedAccount(
            id=uuid.uuid4(),
            identity_id=identity_id or uuid.uuid4(),
            provider="telegram",
            provider_sub_id=f"{uuid.uuid4().int % 1000000000}",
            provider_email=None,
            email_verified=False,
            provider_metadata={
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "language_code": "en",
                "is_premium": False,
                "photo_url": None,
                "allows_write_to_pm": True,
            },
            created_at=now,
            updated_at=now,
        )
