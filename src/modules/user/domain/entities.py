"""User aggregate root entity.

Defines the User aggregate root which holds personal profile information (PII).
The User shares a primary key with the Identity bounded context via a 1:1
relationship (user.id == identity.id).
"""

import uuid
from datetime import UTC, datetime

from attr import dataclass

from src.shared.interfaces.entities import AggregateRoot

_UPDATABLE_FIELDS = frozenset({"profile_email", "first_name", "last_name", "phone"})


@dataclass
class User(AggregateRoot):
    """Aggregate root representing a user profile with PII data.

    Uses a shared primary key with the Identity aggregate (user.id == identity.id)
    to maintain a 1:1 relationship across bounded contexts without tight coupling.

    Attributes:
        id: Unique identifier shared with the corresponding Identity.
        profile_email: Optional display email, may differ from the login email.
        first_name: User's first name.
        last_name: User's last name.
        phone: Optional phone number.
        created_at: Timestamp of when the user was created.
        updated_at: Timestamp of the last profile update.
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
        """Create a new User from an Identity registration event.

        Initializes the user with empty name fields and the shared primary key
        from the Identity aggregate.

        Args:
            identity_id: The Identity aggregate ID to use as the shared PK.
            profile_email: Optional display email for the user profile.

        Returns:
            A new User instance with default empty profile fields.
        """
        now = datetime.now(UTC)
        return cls(
            id=identity_id,
            profile_email=profile_email,
            first_name="",
            last_name="",
            phone=None,
            created_at=now,
            updated_at=now,
        )

    def update_profile(self, **kwargs: str | None) -> None:
        """Update profile fields with the provided keyword arguments.

        Only fields listed in ``_UPDATABLE_FIELDS`` are accepted; unknown
        keys are silently ignored. The ``updated_at`` timestamp is always
        refreshed.

        Args:
            **kwargs: Field-value pairs to update. Accepted keys are
                ``profile_email``, ``first_name``, ``last_name``, and ``phone``.
        """
        for field, value in kwargs.items():
            if field in _UPDATABLE_FIELDS:
                setattr(self, field, value)
        self.updated_at = datetime.now(UTC)

    def anonymize(self) -> None:
        """Anonymize all PII fields for GDPR compliance.

        Replaces name fields with ``[DELETED]``, clears phone and email,
        and updates the ``updated_at`` timestamp.
        """
        self.first_name = "[DELETED]"
        self.last_name = "[DELETED]"
        self.phone = None
        self.profile_email = None
        self.updated_at = datetime.now(UTC)
