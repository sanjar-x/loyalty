"""
Logistics domain exceptions.

Extends the shared ``AppException`` hierarchy.
Part of the domain layer — zero framework imports.
"""

from typing import Any

from src.shared.exceptions import (
    AppException,
    ConflictError,
    NotFoundError,
    ValidationError,
)


class ProviderUnavailableError(AppException):
    """Raised when a logistics provider API is unreachable or timed out (HTTP 503)."""

    def __init__(
        self,
        message: str = "Logistics provider is temporarily unavailable",
        error_code: str = "PROVIDER_UNAVAILABLE",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=503,
            error_code=error_code,
            details=details,
        )


class ShipmentNotFoundError(NotFoundError):
    """Raised when a shipment does not exist (HTTP 404)."""

    def __init__(
        self,
        message: str = "Shipment not found",
        error_code: str = "SHIPMENT_NOT_FOUND",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
        )


class InvalidShipmentTransitionError(ConflictError):
    """Raised when a Shipment FSM transition is not allowed (HTTP 409)."""

    def __init__(
        self,
        current_status: str,
        target_status: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=f"Cannot transition from '{current_status}' to '{target_status}'",
            error_code="INVALID_SHIPMENT_TRANSITION",
            details=details
            or {"current_status": current_status, "target_status": target_status},
        )


class RateCalculationError(AppException):
    """Raised when all providers failed to return rates (HTTP 502)."""

    def __init__(
        self,
        message: str = "Failed to calculate shipping rates",
        error_code: str = "RATE_CALCULATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=502,
            error_code=error_code,
            details=details,
        )


class BookingError(AppException):
    """Raised when the logistics provider rejected a booking request (HTTP 502)."""

    def __init__(
        self,
        message: str = "Provider rejected booking request",
        error_code: str = "BOOKING_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=502,
            error_code=error_code,
            details=details,
        )


class CancellationError(ConflictError):
    """Raised when a shipment cannot be cancelled (HTTP 409)."""

    def __init__(
        self,
        message: str = "Shipment cannot be cancelled in its current state",
        error_code: str = "CANCELLATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
        )


class NoEligibleProvidersError(ValidationError):
    """Raised when no providers match the given route/parcel constraints (HTTP 400)."""

    def __init__(
        self,
        message: str = "No logistics providers eligible for this shipment",
        error_code: str = "NO_ELIGIBLE_PROVIDERS",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
        )
