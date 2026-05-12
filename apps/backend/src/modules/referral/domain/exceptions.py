"""Referral domain exceptions.

Each exception carries an HTTP status code via the
:class:`AppException` hierarchy so the global FastAPI exception handler
maps them to the right response without ad-hoc translation.
"""

from __future__ import annotations

from shared.exceptions import (
    AppException,
    ConflictError,
    NotFoundError,
    ValidationError,
)

# ---------------------------------------------------------------------------
# ReferralCode
# ---------------------------------------------------------------------------


class ReferralCodeNotFoundError(NotFoundError):
    def __init__(self, *, code: str | None = None) -> None:
        super().__init__(
            message=f"Referral code not found: {code}"
            if code
            else "Referral code not found",
            error_code="REFERRAL_CODE_NOT_FOUND",
            details={"code": code} if code else None,
        )


class ReferralCodeAlreadyIssuedError(ConflictError):
    """Raised when a Customer already owns a referral code."""

    def __init__(self) -> None:
        super().__init__(
            message="Customer already owns a referral code",
            error_code="REFERRAL_CODE_ALREADY_ISSUED",
        )


class ReferralCodeRevokedError(ConflictError):
    """Raised when an attempt is made to attribute through a revoked code."""

    def __init__(self) -> None:
        super().__init__(
            message="Referral code has been revoked",
            error_code="REFERRAL_CODE_REVOKED",
        )


# ---------------------------------------------------------------------------
# Referral graph
# ---------------------------------------------------------------------------


class SelfReferralError(ValidationError):
    """A customer attempted to attribute themselves as their own referrer."""

    def __init__(self) -> None:
        super().__init__(
            message="Self-referral is not permitted",
            error_code="REFERRAL_SELF_ATTRIBUTION",
        )


class ReferralAlreadyAttributedError(ConflictError):
    """First-touch attribution: an invitee may have at most one referrer."""

    def __init__(self) -> None:
        super().__init__(
            message="Invitee is already attributed to a referrer (first-touch wins)",
            error_code="REFERRAL_ALREADY_ATTRIBUTED",
        )


class ReferralExpiredError(ConflictError):
    """The referral expired before activation."""

    def __init__(self) -> None:
        super().__init__(
            message="Referral has expired",
            error_code="REFERRAL_EXPIRED",
        )


class ReferralInvalidTransitionError(ConflictError):
    """Referral FSM rejected the requested transition."""

    def __init__(self, *, current: str, target: str) -> None:
        super().__init__(
            message=f"Cannot transition referral from {current} to {target}",
            error_code="REFERRAL_INVALID_TRANSITION",
            details={"current": current, "target": target},
        )


class ReferralAlreadyTerminalError(ConflictError):
    """Attempted transition out of a terminal referral state."""

    def __init__(self, *, status: str) -> None:
        super().__init__(
            message=f"Referral is already terminal: {status}",
            error_code="REFERRAL_ALREADY_TERMINAL",
            details={"status": status},
        )


# ---------------------------------------------------------------------------
# ReferralReward
# ---------------------------------------------------------------------------


class RewardCapExceededError(ConflictError):
    """Monthly / daily reward cap has been hit."""

    def __init__(self, *, cap_kind: str, limit: int) -> None:
        super().__init__(
            message=f"Reward cap exceeded: {cap_kind} (limit={limit})",
            error_code="REFERRAL_REWARD_CAP_EXCEEDED",
            details={"cap_kind": cap_kind, "limit": limit},
        )


class RewardInvalidStateError(ConflictError):
    """Reward state machine rejected the operation."""

    def __init__(self, *, current: str, attempted: str) -> None:
        super().__init__(
            message=f"Cannot {attempted} reward in state {current}",
            error_code="REFERRAL_REWARD_INVALID_STATE",
            details={"current": current, "attempted": attempted},
        )


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------


class ReferralProgrammeUnavailableError(AppException):
    """Returned to invitees when their attribution was rejected (fraud / cap)."""

    def __init__(self) -> None:
        super().__init__(
            message="Loyalty programme is not available for this attribution",
            status_code=403,
            error_code="REFERRAL_PROGRAMME_UNAVAILABLE",
        )
