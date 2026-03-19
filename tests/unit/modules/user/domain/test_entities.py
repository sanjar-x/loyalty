import uuid
from datetime import UTC, datetime

from src.modules.user.domain.entities import User
from tests.factories.user_mothers import UserMothers


class TestUser:
    def _make_user(
        self,
        first_name: str = "John",
        last_name: str = "Doe",
        phone: str | None = "+1234567890",
        profile_email: str | None = "user@example.com",
    ) -> User:
        now = datetime.now(UTC)
        return User(
            id=uuid.uuid4(),
            profile_email=profile_email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            created_at=now,
            updated_at=now,
        )

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

    def test_create_from_identity_uses_shared_pk(self):
        identity_id = uuid.uuid4()
        user = UserMothers.active(identity_id=identity_id)
        assert user.id == identity_id

    def test_update_profile_partial_fields(self):
        user = UserMothers.with_profile(first_name="John", last_name="Doe")
        user.update_profile(first_name="Jane")
        assert user.first_name == "Jane"
        assert user.last_name == "Doe"  # unchanged

    def test_anonymized_mother_replaces_pii(self):
        user = UserMothers.anonymized()
        assert user.first_name == "[DELETED]"
        assert user.last_name == "[DELETED]"
        assert user.phone is None
        assert user.profile_email is None
