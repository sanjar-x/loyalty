# src/modules/user/domain/entities.py
import uuid
from datetime import UTC, datetime

from attr import dataclass

from src.shared.interfaces.entities import AggregateRoot

_UPDATABLE_FIELDS = frozenset({"profile_email", "first_name", "last_name", "phone"})


@dataclass
class User(AggregateRoot):
    """
    Aggregate Root: user profile (PII).
    Shared PK with Identity (user.id == identity.id).
    """

    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_from_identity(
        cls,
        identity_id: uuid.UUID,
        profile_email: str | None = None,
    ) -> User:
        now = datetime.now(UTC)
        return cls(
            id=identity_id,  # Shared PK
            profile_email=profile_email,
            first_name="",
            last_name="",
            phone=None,
            created_at=now,
            updated_at=now,
        )

    def update_profile(self, **kwargs: str | None) -> None:
        for field, value in kwargs.items():
            if field in _UPDATABLE_FIELDS:
                setattr(self, field, value)
        self.updated_at = datetime.now(UTC)

    def anonymize(self) -> None:
        """GDPR: replace all PII with '[DELETED]'."""
        self.first_name = "[DELETED]"
        self.last_name = "[DELETED]"
        self.phone = None
        self.profile_email = None
        self.updated_at = datetime.now(UTC)
