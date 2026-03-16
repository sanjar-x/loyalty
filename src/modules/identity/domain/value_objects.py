# src/modules/identity/domain/value_objects.py
import enum
from dataclasses import dataclass


class IdentityType(str, enum.Enum):
    """Type of identity authentication method."""

    LOCAL = "LOCAL"
    OIDC = "OIDC"


@dataclass(frozen=True, slots=True)
class PermissionCode:
    """
    Value object for permission codename in 'resource:action' format.
    Validates format on creation. Immutable and hashable.
    """

    _value: str

    def __post_init__(self) -> None:
        parts = self._value.split(":")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Permission codename must be in 'resource:action' format, got: '{self._value}'"
            )

    @property
    def resource(self) -> str:
        return self._value.split(":")[0]

    @property
    def action(self) -> str:
        return self._value.split(":")[1]

    def __str__(self) -> str:
        return self._value
