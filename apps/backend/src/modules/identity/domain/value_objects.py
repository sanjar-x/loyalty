"""Value objects for the Identity module.

Contains immutable, side-effect-free types that carry domain meaning
without identity. Value objects are compared by structural equality.
"""

import enum
from dataclasses import dataclass


class PrimaryAuthMethod(enum.StrEnum):
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


class AuthProvider(enum.StrEnum):
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
    {
        AuthProvider.GOOGLE,
        AuthProvider.APPLE,
    }
)


class AccountType(enum.StrEnum):
    """Distinguishes customer accounts from staff/admin accounts.

    Attributes:
        CUSTOMER: Regular end-user account.
        STAFF: Internal staff or admin account.
    """

    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"


class InvitationStatus(enum.StrEnum):
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
