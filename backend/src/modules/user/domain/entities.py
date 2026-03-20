"""User domain entities.

Defines Customer and StaffMember aggregate roots which hold personal
profile information (PII). Both share a primary key with the Identity
bounded context via a 1:1 relationship (entity.id == identity.id).
"""

import uuid
from datetime import UTC, datetime

from attr import dataclass

from src.shared.interfaces.entities import AggregateRoot

_UPDATABLE_FIELDS = frozenset({"profile_email", "first_name", "last_name", "phone"})


@dataclass
class User(AggregateRoot):
    """Aggregate root representing a user profile with PII data.

    .. deprecated::
        Use :class:`Customer` or :class:`StaffMember` instead.

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

    # deprecated — use Customer or StaffMember instead
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


_CUSTOMER_UPDATABLE_FIELDS = frozenset({
    "profile_email",
    "first_name",
    "last_name",
    "phone",
    "username",
})


@dataclass
class Customer(AggregateRoot):
    """Aggregate root -- customer profile (buyer).

    Shared PK with Identity (customer.id == identity.id).
    Referral code is auto-generated on creation.

    Attributes:
        id: UUID = identity.id (shared PK).
        profile_email: Display email (may differ from login email).
        first_name: First name.
        last_name: Last name.
        phone: Phone number.
        referral_code: Unique referral code (8 chars, auto-generated).
        referred_by: Customer ID of the referrer (None if organic).
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    username: str | None
    phone: str | None
    referral_code: str
    referred_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_from_identity(
        cls,
        identity_id: uuid.UUID,
        profile_email: str | None = None,
        first_name: str = "",
        last_name: str = "",
        username: str | None = None,
        referral_code: str | None = None,
        referred_by: uuid.UUID | None = None,
    ) -> Customer:
        """Create a new Customer from an Identity registration event.

        Args:
            identity_id: The Identity aggregate ID to use as the shared PK.
            profile_email: Optional display email.
            first_name: Customer's first name (from credentials provider).
            last_name: Customer's last name (from credentials provider).
            referral_code: Unique referral code (generated in handler if not provided).
            referred_by: Customer ID of the referrer, if any.

        Returns:
            A new Customer instance.
        """
        now = datetime.now(UTC)
        return cls(
            id=identity_id,
            profile_email=profile_email,
            first_name=first_name,
            last_name=last_name,
            username=username,
            phone=None,
            referral_code=referral_code or "",
            referred_by=referred_by,
            created_at=now,
            updated_at=now,
        )

    def update_profile(self, **kwargs: str | None) -> None:
        """Update profile fields.

        Only fields in ``_CUSTOMER_UPDATABLE_FIELDS`` are accepted;
        unknown keys are silently ignored.

        Args:
            **kwargs: Field-value pairs to update. Accepted keys are
                ``profile_email``, ``first_name``, ``last_name``, ``phone``,
                and ``username``.
        """
        for field, value in kwargs.items():
            if field in _CUSTOMER_UPDATABLE_FIELDS:
                setattr(self, field, value)
        self.updated_at = datetime.now(UTC)

    def anonymize(self) -> None:
        """GDPR anonymization. Referral code is preserved (not PII)."""
        self.first_name = "[DELETED]"
        self.last_name = "[DELETED]"
        self.phone = None
        self.profile_email = None
        self.username = None
        self.updated_at = datetime.now(UTC)


_STAFF_UPDATABLE_FIELDS = frozenset({
    "first_name",
    "last_name",
    "position",
    "department",
})


@dataclass
class StaffMember(AggregateRoot):
    """Aggregate root -- staff member profile.

    Shared PK with Identity (staff_member.id == identity.id).
    Created upon acceptance of a StaffInvitation.

    Attributes:
        id: UUID = identity.id (shared PK).
        first_name: First name.
        last_name: Last name.
        profile_email: Display email.
        position: Job position.
        department: Department name.
        invited_by: Identity ID of the admin who invited this staff member.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    first_name: str
    last_name: str
    profile_email: str | None
    position: str | None
    department: str | None
    invited_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_from_invitation(
        cls,
        identity_id: uuid.UUID,
        profile_email: str | None,
        invited_by: uuid.UUID,
        first_name: str = "",
        last_name: str = "",
    ) -> StaffMember:
        """Create a new StaffMember from an invitation acceptance.

        Args:
            identity_id: The Identity aggregate ID to use as the shared PK.
            profile_email: Display email.
            invited_by: Identity ID of the inviting admin.
            first_name: First name (optional).
            last_name: Last name (optional).

        Returns:
            A new StaffMember instance.
        """
        now = datetime.now(UTC)
        return cls(
            id=identity_id,
            first_name=first_name,
            last_name=last_name,
            profile_email=profile_email,
            position=None,
            department=None,
            invited_by=invited_by,
            created_at=now,
            updated_at=now,
        )

    def update_profile(self, **kwargs: str | None) -> None:
        """Update profile fields.

        Only fields in ``_STAFF_UPDATABLE_FIELDS`` are accepted;
        unknown keys are silently ignored.

        Args:
            **kwargs: Field-value pairs to update. Accepted keys are
                ``first_name``, ``last_name``, ``position``, and ``department``.
        """
        for field, value in kwargs.items():
            if field in _STAFF_UPDATABLE_FIELDS:
                setattr(self, field, value)
        self.updated_at = datetime.now(UTC)
