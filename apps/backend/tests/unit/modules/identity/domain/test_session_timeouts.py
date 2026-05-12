import uuid
from datetime import UTC, datetime, timedelta

from src.modules.identity.domain.entities import Session
from src.modules.identity.domain.exceptions import SessionExpiredError


class TestSessionIdleTimeout:
    def test_create_sets_idle_expires_at(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="test-token",
            ip_address="127.0.0.1",
            user_agent="Test/1.0",
            role_ids=[],
            expires_days=30,
            idle_timeout_minutes=30,
        )
        assert session.idle_expires_at > session.created_at
        assert session.idle_expires_at <= session.created_at + timedelta(minutes=31)
        assert session.last_active_at == session.created_at

    def test_touch_extends_idle_timeout(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="test-token",
            ip_address="127.0.0.1",
            user_agent="Test/1.0",
            role_ids=[],
            expires_days=30,
            idle_timeout_minutes=15,
        )
        old_idle = session.idle_expires_at
        session.touch(idle_timeout_minutes=15)
        assert session.idle_expires_at >= old_idle
        assert session.last_active_at >= session.created_at

    def test_ensure_valid_raises_on_idle_expiry(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="test-token",
            ip_address="127.0.0.1",
            user_agent="Test/1.0",
            role_ids=[],
            expires_days=30,
            idle_timeout_minutes=30,
        )
        session.idle_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        try:
            session.ensure_valid()
            raise AssertionError("Should have raised SessionExpiredError")
        except SessionExpiredError:
            pass

    def test_ensure_valid_passes_when_both_valid(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="test-token",
            ip_address="127.0.0.1",
            user_agent="Test/1.0",
            role_ids=[],
            expires_days=30,
            idle_timeout_minutes=30,
        )
        session.ensure_valid()
