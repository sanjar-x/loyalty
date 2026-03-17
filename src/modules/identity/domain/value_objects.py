"""Value objects for the Identity module.

Contains immutable, side-effect-free types that carry domain meaning
without identity. Value objects are compared by structural equality.
"""

import enum
from dataclasses import dataclass


class IdentityType(str, enum.Enum):
    """Authentication method used by an identity.

    Attributes:
        LOCAL: Email and password authentication.
        OIDC: External OpenID Connect provider authentication.
    """

    LOCAL = "LOCAL"
    OIDC = "OIDC"


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
                f"Permission codename must be in 'resource:action' format, got: '{self._value}'"
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
