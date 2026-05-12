"""Order domain exceptions."""

from shared.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
    ValidationError,
)


class OrderNotFoundError(NotFoundError):
    def __init__(self, *, order_id: str | None = None) -> None:
        super().__init__(
            message=f"Order not found: {order_id}" if order_id else "Order not found",
            error_code="ORDER_NOT_FOUND",
        )


class OrderInvalidTransitionError(ConflictError):
    def __init__(self, *, current: str, target: str) -> None:
        super().__init__(
            message=f"Cannot transition order from {current} to {target}",
            error_code="ORDER_INVALID_TRANSITION",
            details={"current": current, "target": target},
        )


class OrderAlreadyTerminalError(ConflictError):
    def __init__(self, *, status: str) -> None:
        super().__init__(
            message=f"Order is in terminal state: {status}",
            error_code="ORDER_ALREADY_TERMINAL",
            details={"status": status},
        )


class OrderEmptyError(UnprocessableEntityError):
    def __init__(self) -> None:
        super().__init__(
            message="Cannot create an order with zero items",
            error_code="ORDER_EMPTY",
        )


class OrderItemQuantityError(ValidationError):
    def __init__(self, *, quantity: int) -> None:
        super().__init__(
            message=f"Invalid order item quantity: {quantity}",
            error_code="ORDER_ITEM_QUANTITY_ERROR",
        )


class OrderHoldStateError(ConflictError):
    def __init__(self, *, status: str) -> None:
        super().__init__(
            message=f"Order in {status} cannot be put on hold or resumed",
            error_code="ORDER_HOLD_INVALID",
            details={"current": status},
        )


class IdempotencyKeyConflictError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            message="Idempotency key already used with a different request",
            error_code="IDEMPOTENCY_KEY_CONFLICT",
        )


class IncomingDeclarationConflictError(ConflictError):
    def __init__(self, *, declaration: str) -> None:
        super().__init__(
            message=f"Incoming declaration already used: {declaration}",
            error_code="INCOMING_DECLARATION_CONFLICT",
            details={"declaration": declaration},
        )


class PickupPointChangeForbiddenError(ConflictError):
    def __init__(self, *, status: str) -> None:
        super().__init__(
            message=f"Cannot change pickup point in status {status}",
            error_code="PICKUP_POINT_CHANGE_FORBIDDEN",
            details={"current": status},
        )


class CancellationForbiddenError(ConflictError):
    def __init__(self, *, status: str) -> None:
        super().__init__(
            message=(
                f"Cannot cancel order in status {status} — use return flow instead"
            ),
            error_code="CANCELLATION_FORBIDDEN",
            details={"current": status},
        )


class CrossBorderProviderError(ConflictError):
    """Failure reported by an external cross-border provider (e.g. DobroPost)."""

    def __init__(self, *, provider: str, reason: str) -> None:
        super().__init__(
            message=f"Cross-border provider {provider} rejected request: {reason}",
            error_code="CROSS_BORDER_PROVIDER_ERROR",
            details={"provider": provider, "reason": reason},
        )
