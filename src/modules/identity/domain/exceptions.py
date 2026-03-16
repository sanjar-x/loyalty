# src/modules/identity/domain/exceptions.py
from src.shared.exceptions import (
    AppException,
    ConflictError,
    ForbiddenError,
    UnauthorizedError,
    UnprocessableEntityError,
)


class InvalidCredentialsError(UnauthorizedError):
    """Unified error for wrong email OR wrong password (user enumeration protection)."""

    def __init__(self) -> None:
        super().__init__(
            message="Invalid email or password",
            error_code="INVALID_CREDENTIALS",
        )


class IdentityAlreadyExistsError(ConflictError):
    """Email already registered."""

    def __init__(self, email: str) -> None:
        super().__init__(
            message="Email already registered",
            error_code="IDENTITY_ALREADY_EXISTS",
            details={"email": email},
        )


class IdentityDeactivatedError(ForbiddenError):
    """Identity account is deactivated."""

    def __init__(self) -> None:
        super().__init__(
            message="Account is deactivated",
            error_code="IDENTITY_DEACTIVATED",
        )


class SessionExpiredError(UnauthorizedError):
    """Refresh token expired (> 30 days)."""

    def __init__(self) -> None:
        super().__init__(
            message="Session expired",
            error_code="SESSION_EXPIRED",
        )


class SessionRevokedError(UnauthorizedError):
    """Session was revoked (logout or reuse detection)."""

    def __init__(self) -> None:
        super().__init__(
            message="Session revoked",
            error_code="SESSION_REVOKED",
        )


class RefreshTokenReuseError(UnauthorizedError):
    """Reuse of old refresh token detected — all sessions revoked."""

    def __init__(self) -> None:
        super().__init__(
            message="Token reuse detected, all sessions revoked",
            error_code="REFRESH_TOKEN_REUSE",
        )


class MaxSessionsExceededError(AppException):
    """Exceeded maximum active sessions per identity (default: 5). HTTP 429."""

    def __init__(self, max_sessions: int) -> None:
        super().__init__(
            message="Maximum active sessions limit reached",
            status_code=429,
            error_code="MAX_SESSIONS_EXCEEDED",
            details={"max_sessions": max_sessions},
        )


class RoleHierarchyCycleError(UnprocessableEntityError):
    """Attempt to create a cycle in role hierarchy."""

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
    """Cannot modify or delete system roles (is_system=True)."""

    def __init__(self, role_name: str) -> None:
        super().__init__(
            message="System roles cannot be modified",
            error_code="SYSTEM_ROLE_MODIFICATION",
            details={"role_name": role_name},
        )


class InsufficientPermissionsError(ForbiddenError):
    """RequirePermission check failed — session lacks required permission."""

    def __init__(self, codename: str | None = None) -> None:
        super().__init__(
            message="Insufficient permissions",
            error_code="INSUFFICIENT_PERMISSIONS",
            details={"required_permission": codename} if codename else {},
        )
