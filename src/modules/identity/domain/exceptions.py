"""Domain exceptions for the Identity module.

Each exception maps to a specific HTTP status code and machine-readable error
code, enabling consistent API error responses across the identity bounded context.
"""

from src.shared.exceptions import (
    AppException,
    ConflictError,
    ForbiddenError,
    UnauthorizedError,
    UnprocessableEntityError,
)


class InvalidCredentialsError(UnauthorizedError):
    """Raised when email or password verification fails.

    Uses a unified message to prevent user enumeration attacks.
    """

    def __init__(self) -> None:
        super().__init__(
            message="Invalid email or password",
            error_code="INVALID_CREDENTIALS",
        )


class IdentityAlreadyExistsError(ConflictError):
    """Raised when attempting to register with an already-registered email."""

    def __init__(self) -> None:
        super().__init__(
            message="Email already registered",
            error_code="IDENTITY_ALREADY_EXISTS",
        )


class IdentityDeactivatedError(ForbiddenError):
    """Raised when a deactivated identity attempts to authenticate."""

    def __init__(self) -> None:
        super().__init__(
            message="Account is deactivated",
            error_code="IDENTITY_DEACTIVATED",
        )


class SessionExpiredError(UnauthorizedError):
    """Raised when a refresh token has expired (past its TTL)."""

    def __init__(self) -> None:
        super().__init__(
            message="Session expired",
            error_code="SESSION_EXPIRED",
        )


class SessionRevokedError(UnauthorizedError):
    """Raised when a revoked session is used (logout or reuse detection)."""

    def __init__(self) -> None:
        super().__init__(
            message="Session revoked",
            error_code="SESSION_REVOKED",
        )


class RefreshTokenReuseError(UnauthorizedError):
    """Raised when a previously rotated refresh token is reused.

    This indicates a potential token theft; all sessions for the identity
    should be revoked.
    """

    def __init__(self) -> None:
        super().__init__(
            message="Token reuse detected, all sessions revoked",
            error_code="REFRESH_TOKEN_REUSE",
        )


class MaxSessionsExceededError(AppException):
    """Raised when the maximum number of active sessions per identity is reached.

    Returns HTTP 429 (Too Many Requests).

    Args:
        max_sessions: The configured session limit that was exceeded.
    """

    def __init__(self, max_sessions: int) -> None:
        super().__init__(
            message="Maximum active sessions limit reached",
            status_code=429,
            error_code="MAX_SESSIONS_EXCEEDED",
            details={"max_sessions": max_sessions},
        )


class RoleHierarchyCycleError(UnprocessableEntityError):
    """Raised when a role hierarchy operation would create a cycle.

    Args:
        parent_role_id: The parent role in the attempted assignment.
        child_role_id: The child role in the attempted assignment.
    """

    def __init__(self, parent_role_id: str, child_role_id: str) -> None:
        super().__init__(
            message="Role hierarchy cycle detected",
            error_code="ROLE_HIERARCHY_CYCLE",
            details={
                "parent_role_id": parent_role_id,
                "child_role_id": child_role_id,
            },
        )


class SystemRoleModificationError(ForbiddenError):
    """Raised when attempting to modify or delete a system role (is_system=True).

    Args:
        role_name: Name of the system role that was targeted.
    """

    def __init__(self, role_name: str) -> None:
        super().__init__(
            message="System roles cannot be modified",
            error_code="SYSTEM_ROLE_MODIFICATION",
            details={"role_name": role_name},
        )


class InsufficientPermissionsError(ForbiddenError):
    """Raised when a session lacks the required permission for an operation.

    Args:
        codename: The permission codename that was required, if available.
    """

    def __init__(self, codename: str | None = None) -> None:
        super().__init__(
            message="Insufficient permissions",
            error_code="INSUFFICIENT_PERMISSIONS",
            details={"required_permission": codename} if codename else {},
        )
