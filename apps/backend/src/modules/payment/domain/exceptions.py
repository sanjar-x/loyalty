"""Payment domain exceptions."""

from shared.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
)


class PaymentIntentNotFoundError(NotFoundError):
    def __init__(self, *, intent_id: str | None = None) -> None:
        super().__init__(
            message=(
                f"Payment intent not found: {intent_id}"
                if intent_id
                else "Payment intent not found"
            ),
            error_code="PAYMENT_INTENT_NOT_FOUND",
        )


class PaymentIntentInvalidTransitionError(ConflictError):
    def __init__(self, *, current: str, target: str) -> None:
        super().__init__(
            message=(f"Cannot transition payment intent from {current} to {target}"),
            error_code="PAYMENT_INTENT_INVALID_TRANSITION",
            details={"current": current, "target": target},
        )


class PaymentIntentAlreadyTerminalError(ConflictError):
    """Raised when an FSM transition is attempted from a terminal state.

    Distinguishable from :class:`PaymentIntentInvalidTransitionError`
    so observability can separate «moved into terminal long ago» from
    «attempted a non-existent edge». Mandated by ``StateMachineMixin``
    contract -- the mixin checks ``_TERMINAL_STATES`` before
    ``_ALLOWED_TRANSITIONS`` and raises this class for terminal sources.
    """

    def __init__(self, *, status: str) -> None:
        super().__init__(
            message=f"PaymentIntent is in terminal state: {status}",
            error_code="PAYMENT_INTENT_ALREADY_TERMINAL",
            details={"status": status},
        )


class PaymentProviderError(UnprocessableEntityError):
    def __init__(self, *, provider: str, reason: str) -> None:
        super().__init__(
            message=f"Payment provider {provider} rejected request: {reason}",
            error_code="PAYMENT_PROVIDER_REJECTED",
            details={"provider": provider, "reason": reason},
        )


class PaymentSimulationDisabledError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            message="Payment simulation endpoints are disabled in this environment",
            error_code="PAYMENT_SIMULATION_DISABLED",
        )
