# tests/factories/user_mothers.py
"""Object Mothers for User module domain entities."""

import uuid

from src.modules.user.domain.entities import User


class UserMothers:
    """Pre-built User aggregate configurations."""

    @staticmethod
    def active(identity_id: uuid.UUID | None = None) -> User:
        """Standard active user with profile data."""
        return User.create_from_identity(
            identity_id=identity_id or uuid.uuid4(),
            profile_email="user@example.com",
        )

    @staticmethod
    def with_profile(
        first_name: str = "John",
        last_name: str = "Doe",
        phone: str = "+1234567890",
        identity_id: uuid.UUID | None = None,
    ) -> User:
        """User with full profile populated."""
        user = User.create_from_identity(
            identity_id=identity_id or uuid.uuid4(),
            profile_email="user@example.com",
        )
        user.update_profile(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )
        return user

    @staticmethod
    def anonymized(identity_id: uuid.UUID | None = None) -> User:
        """User after GDPR anonymization — PII replaced."""
        user = UserMothers.with_profile(identity_id=identity_id)
        user.anonymize()
        return user
