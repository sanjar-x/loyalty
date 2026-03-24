"""Value objects for the Identity module.

Contains immutable, side-effect-free types that carry domain meaning
without identity. Value objects are compared by structural equality.
"""

import enum
from dataclasses import dataclass


class PrimaryAuthMethod(str, enum.Enum):
    """Authentication method used by an identity.

    Attributes:
        LOCAL: Email and password authentication.
        OIDC: External OpenID Connect provider authentication.
        TELEGRAM: Telegram Mini App authentication.
    """

    LOCAL = "LOCAL"
    OIDC = "OIDC"
    TELEGRAM = "TELEGRAM"


# Backward-compat alias — existing code imports IdentityType.
IdentityType = PrimaryAuthMethod


class AuthProvider(str, enum.Enum):
    """Third-party authentication provider identifier.

    Attributes:
        TELEGRAM: Telegram messenger.
        GOOGLE: Google OAuth / OIDC.
        APPLE: Apple Sign-In.
    """

    TELEGRAM = "telegram"
    GOOGLE = "google"
    APPLE = "apple"


TRUSTED_EMAIL_PROVIDERS: frozenset[AuthProvider] = frozenset(
    {AuthProvider.GOOGLE, AuthProvider.APPLE}
)


class AccountType(str, enum.Enum):
    """Distinguishes customer accounts from staff/admin accounts.

    Attributes:
        CUSTOMER: Regular end-user account.
        STAFF: Internal staff or admin account.
    """

    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"


class InvitationStatus(str, enum.Enum):
    """Lifecycle status of a staff invitation.

    Attributes:
        PENDING: Invitation sent but not yet accepted.
        ACCEPTED: Invitation accepted and staff account created.
        EXPIRED: Invitation passed its TTL without being accepted.
        REVOKED: Invitation manually revoked by an admin.
    """

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class PermissionCode:
    """Immutable value object for a permission codename in 'resource:action' format.

    Validates the format on creation and provides typed access to the
    resource and action components. Hashable for use in sets and as dict keys.

    Attributes:
        _value: The raw codename string (e.g. "orders:read").
    """

    _value: str

    def __post_init__(self) -> None:
        """Validate that the codename follows the 'resource:action' format.

        Raises:
            ValueError: If the codename is not in 'resource:action' format.
        """
        parts = self._value.split(":")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Permission codename must be 'resource:action', got: '{self._value}'"
            )

    @property
    def resource(self) -> str:
        """Return the resource portion of the codename."""
        return self._value.split(":")[0]

    @property
    def action(self) -> str:
        """Return the action portion of the codename."""
        return self._value.split(":")[1]

    def __str__(self) -> str:
        """Return the raw codename string."""
        return self._value


@dataclass(frozen=True, slots=True)
class TelegramUserData:
    """Immutable snapshot of Telegram user data from initData."""

    telegram_id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool
    photo_url: str | None
    allows_write_to_pm: bool
    start_param: str | None
