"""Domain exceptions for the Identity module.

Each exception maps to a specific HTTP status code and machine-readable error
code, enabling consistent API error responses across the identity bounded context.
"""

from src.shared.exceptions import (
    AppException,
    ConflictError,
    ForbiddenError,
    NotFoundError,
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

    The required codename is stored for server-side logging but NOT
    exposed in the HTTP response to avoid reconnaissance.

    Args:
        codename: The permission codename that was required (logged, not exposed).
    """

    def __init__(self, codename: str | None = None) -> None:
        super().__init__(
            message="Insufficient permissions",
            error_code="INSUFFICIENT_PERMISSIONS",
        )
        self.required_codename = codename


class IdentityAlreadyDeactivatedError(ConflictError):
    """Raised when attempting to deactivate an already-deactivated identity."""

    def __init__(self) -> None:
        super().__init__(
            message="Identity is already deactivated",
            error_code="IDENTITY_ALREADY_DEACTIVATED",
        )


class IdentityAlreadyActiveError(ConflictError):
    """Raised when attempting to reactivate an already-active identity."""

    def __init__(self) -> None:
        super().__init__(
            message="Identity is already active",
            error_code="IDENTITY_ALREADY_ACTIVE",
        )


class SelfDeactivationError(ForbiddenError):
    """Raised when an admin attempts to deactivate their own identity."""

    def __init__(self) -> None:
        super().__init__(
            message="Cannot deactivate your own identity",
            error_code="SELF_DEACTIVATION_FORBIDDEN",
        )


class LastAdminProtectionError(ForbiddenError):
    """Raised when attempting to deactivate/remove the last admin."""

    def __init__(self) -> None:
        super().__init__(
            message="Cannot remove the last admin",
            error_code="LAST_ADMIN_PROTECTION",
        )


class PrivilegeEscalationError(ForbiddenError):
    """Raised when an admin attempts to grant permissions they don't hold.

    Args:
        escalated_permissions: List of permission codenames the admin doesn't have.
    """

    def __init__(self, escalated_permissions: list[str]) -> None:
        super().__init__(
            message="Cannot grant permissions you don't hold",
            error_code="PRIVILEGE_ESCALATION",
            details={"escalated_permissions": escalated_permissions},
        )


class InvitationNotFoundError(NotFoundError):
    """Raised when a staff invitation is not found."""

    def __init__(self) -> None:
        super().__init__(
            message="Staff invitation not found",
            error_code="INVITATION_NOT_FOUND",
        )


class InvitationExpiredError(AppException):
    """Raised when a staff invitation has expired (TTL exceeded)."""

    def __init__(self) -> None:
        super().__init__(
            message="Staff invitation has expired",
            status_code=410,
            error_code="INVITATION_EXPIRED",
        )


class InvitationAlreadyAcceptedError(ConflictError):
    """Raised when attempting to accept an already-accepted invitation."""

    def __init__(self) -> None:
        super().__init__(
            message="Staff invitation already accepted",
            error_code="INVITATION_ALREADY_ACCEPTED",
        )


class InvitationRevokedError(ForbiddenError):
    """Raised when attempting to use a revoked invitation."""

    def __init__(self) -> None:
        super().__init__(
            message="Staff invitation has been revoked",
            error_code="INVITATION_REVOKED",
        )


class InvitationNotPendingError(ConflictError):
    """Raised when an operation requires PENDING status but invitation is not."""

    def __init__(self) -> None:
        super().__init__(
            message="Invitation is not in pending status",
            error_code="INVITATION_NOT_PENDING",
        )


class ActiveInvitationExistsError(ConflictError):
    """Raised when a pending invitation already exists for the given email."""

    def __init__(self) -> None:
        super().__init__(
            message="Active invitation for this email already exists",
            error_code="ACTIVE_INVITATION_EXISTS",
        )


class AccountTypeMismatchError(ForbiddenError):
    """Raised when a role is incompatible with the identity's account type."""

    def __init__(self) -> None:
        super().__init__(
            message="Role is not compatible with account type",
            error_code="ACCOUNT_TYPE_MISMATCH",
        )


class RoleAlreadyAssignedError(ConflictError):
    """Raised when attempting to assign a role that is already assigned."""

    def __init__(self) -> None:
        super().__init__(
            message="Role is already assigned to this identity",
            error_code="ROLE_ALREADY_ASSIGNED",
        )
