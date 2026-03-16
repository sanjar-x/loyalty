import uuid
from datetime import datetime, timezone

from src.modules.user.domain.entities import User


class TestUser:
    def _make_user(self, **kwargs) -> User:
        defaults = {
            "id": uuid.uuid4(),
            "profile_email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        defaults.update(kwargs)
        return User(**defaults)

    def test_create_from_identity(self):
        identity_id = uuid.uuid4()
        user = User.create_from_identity(
            identity_id=identity_id,
            profile_email="user@example.com",
        )
        assert user.id == identity_id  # Shared PK
        assert user.profile_email == "user@example.com"
        assert user.first_name == ""
        assert user.last_name == ""

    def test_update_profile(self):
        user = self._make_user()
        user.update_profile(first_name="Jane", phone="+9876543210")
        assert user.first_name == "Jane"
        assert user.phone == "+9876543210"
        assert user.last_name == "Doe"  # unchanged

    def test_update_profile_ignores_unknown_fields(self):
        user = self._make_user()
        user.update_profile(unknown_field="value")
        # should not raise, unknown fields are silently ignored

    def test_anonymize_replaces_pii(self):
        user = self._make_user(
            first_name="John",
            last_name="Doe",
            phone="+1234567890",
            profile_email="user@example.com",
        )
        user.anonymize()
        assert user.first_name == "[DELETED]"
        assert user.last_name == "[DELETED]"
        assert user.phone is None
        assert user.profile_email is None

    def test_anonymize_is_idempotent(self):
        user = self._make_user()
        user.anonymize()
        user.anonymize()  # should not raise
        assert user.first_name == "[DELETED]"
