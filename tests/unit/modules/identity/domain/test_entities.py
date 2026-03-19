import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.modules.identity.domain.entities import (
    Identity,
    LinkedAccount,
    LocalCredentials,
    Permission,
    Role,
    Session,
)
from src.modules.identity.domain.events import (
    IdentityDeactivatedEvent,
    IdentityReactivatedEvent,
)
from src.modules.identity.domain.exceptions import (
    IdentityDeactivatedError,
    RefreshTokenReuseError,
    SessionExpiredError,
)
from src.modules.identity.domain.value_objects import IdentityType
from tests.factories.identity_mothers import IdentityMothers


class TestIdentity:
    def test_register_creates_active_identity(self):
        identity = Identity.register(IdentityType.LOCAL)
        assert identity.is_active is True
        assert identity.type == IdentityType.LOCAL
        assert isinstance(identity.id, uuid.UUID)

    def test_register_emits_no_event(self):
        """register() itself does not emit events — RegisterHandler emits IdentityRegisteredEvent after credentials are created."""
        identity = Identity.register(IdentityType.LOCAL)
        assert len(identity.domain_events) == 0

    def test_deactivate_sets_inactive(self):
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="user_request")
        assert identity.is_active is False

    def test_deactivate_emits_event(self):
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="user_request")
        events = identity.domain_events
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, IdentityDeactivatedEvent)
        assert event.identity_id == identity.id
        assert event.reason == "user_request"

    def test_ensure_active_passes_when_active(self):
        identity = Identity.register(IdentityType.LOCAL)
        identity.ensure_active()  # should not raise

    def test_ensure_active_raises_when_deactivated(self):
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="test")
        with pytest.raises(IdentityDeactivatedError):
            identity.ensure_active()

    def test_register_oidc_type(self):
        identity = IdentityMothers.active_oidc()
        assert identity.type == IdentityType.OIDC
        assert identity.is_active is True

    def test_deactivated_mother_has_cleared_events(self):
        identity = IdentityMothers.deactivated()
        assert identity.is_active is False
        assert len(identity.domain_events) == 0

    def test_deactivate_sets_deactivated_by(self):
        admin_id = uuid.uuid4()
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="admin_action", deactivated_by=admin_id)
        assert identity.deactivated_by == admin_id

    def test_deactivate_sets_deactivated_at(self):
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="admin_action", deactivated_by=uuid.uuid4())
        assert identity.deactivated_at is not None

    def test_deactivate_emits_event_with_deactivated_by(self):
        admin_id = uuid.uuid4()
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="admin_action", deactivated_by=admin_id)
        events = identity.domain_events
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, IdentityDeactivatedEvent)
        assert event.deactivated_by == admin_id

    def test_reactivate_clears_deactivated_fields(self):
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="test", deactivated_by=uuid.uuid4())
        identity.clear_domain_events()
        identity.reactivate()
        assert identity.deactivated_at is None
        assert identity.deactivated_by is None

    def test_reactivate_sets_active_true(self):
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="test")
        identity.clear_domain_events()
        identity.reactivate()
        assert identity.is_active is True

    def test_reactivate_emits_event(self):
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="test")
        identity.clear_domain_events()
        identity.reactivate()
        events = identity.domain_events
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, IdentityReactivatedEvent)
        assert event.identity_id == identity.id


class TestLocalCredentials:
    def test_create(self):
        creds = LocalCredentials(
            identity_id=uuid.uuid4(),
            email="user@example.com",
            password_hash="$argon2id$hashed",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert creds.email == "user@example.com"


class TestSession:
    def test_create_hashes_refresh_token(self):
        raw_token = "test-refresh-token-value"
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token=raw_token,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[uuid.uuid4()],
            expires_days=30,
        )

        assert session.refresh_token_hash == expected_hash
        assert session.is_revoked is False
        assert isinstance(session.id, uuid.UUID)

    def test_revoke(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        session.revoke()
        assert session.is_revoked is True

    def test_is_expired_false_when_fresh(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        assert session.is_expired() is False

    def test_is_expired_true_when_past(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)
        assert session.is_expired() is True

    def test_rotate_refresh_token(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="old-token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        old_hash = session.refresh_token_hash
        new_hash = session.rotate_refresh_token("new-token")

        assert session.refresh_token_hash == new_hash
        assert session.refresh_token_hash != old_hash
        assert new_hash == hashlib.sha256(b"new-token").hexdigest()

    def test_verify_refresh_token_passes_on_match(self):
        raw_token = "correct-token"
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token=raw_token,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        session.verify_refresh_token(raw_token)  # should not raise

    def test_verify_refresh_token_raises_on_mismatch(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="correct-token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        with pytest.raises(RefreshTokenReuseError):
            session.verify_refresh_token("wrong-token")

    def test_ensure_valid_raises_when_expired(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)
        with pytest.raises(SessionExpiredError):
            session.ensure_valid()

    def test_ensure_valid_raises_when_revoked(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        session.revoke()
        from src.modules.identity.domain.exceptions import SessionRevokedError

        with pytest.raises(SessionRevokedError):
            session.ensure_valid()


class TestRole:
    def test_create(self):
        role = Role(
            id=uuid.uuid4(),
            name="admin",
            description="Administrator",
            is_system=True,
        )
        assert role.name == "admin"
        assert role.is_system is True


class TestPermission:
    def test_create(self):
        perm = Permission(
            id=uuid.uuid4(),
            codename="brands:create",
            resource="brands",
            action="create",
            description="Create new brands",
        )
        assert perm.codename == "brands:create"
        assert perm.description == "Create new brands"

    def test_description_optional(self):
        perm = Permission(
            id=uuid.uuid4(),
            codename="brands:read",
            resource="brands",
            action="read",
        )
        assert perm.description is None


class TestLinkedAccount:
    def test_create(self):
        account = LinkedAccount(
            id=uuid.uuid4(),
            identity_id=uuid.uuid4(),
            provider="google",
            provider_sub_id="12345",
            provider_email="user@gmail.com",
        )
        assert account.provider == "google"

    def test_ensure_valid_passes_when_fresh(self):
        _, session, _ = IdentityMothers.with_session()
        session.ensure_valid()  # should not raise
