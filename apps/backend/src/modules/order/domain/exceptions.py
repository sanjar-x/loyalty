"""Order domain exceptions."""

from src.shared.exceptions import (
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


class OrderDeliveryAmountInvalidError(ValidationError):
    def __init__(self, *, delivery_amount: int) -> None:
        super().__init__(
            message=f"Invalid order delivery amount: {delivery_amount}",
            error_code="ORDER_DELIVERY_AMOUNT_INVALID",
            details={"delivery_amount": delivery_amount},
        )


class PassportRequiredForCrossBorderError(UnprocessableEntityError):
    """Cross-border item present without an attached passport snapshot.

    Sprint 1.5 Part 2 / ADR-011 invariant. Order.create raises this when
    at least one ``OrderItem.supplier_type == SupplierType.CROSS_BORDER``
    but ``passport_snapshot is None``. Local-only orders are exempt —
    they don't pass through customs.
    """

    def __init__(self) -> None:
        super().__init__(
            message=(
                "Passport is required for cross-border orders. "
                "Attach a passport via ``passport_id`` at checkout."
            ),
            error_code="PASSPORT_REQUIRED_FOR_CROSS_BORDER",
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


class PriceOverrideValidationError(ValidationError):
    """Admin-supplied unit_price override violates configured bounds.

    Bounds: ``0 <= override <= base_price * WALK_IN_MAX_PRICE_OVERRIDE_RATIO``.
    A bound failure is a 400, not 422 — the input is well-formed but
    business-rule rejected.
    """

    def __init__(
        self,
        *,
        sku_id: str,
        base_price: int,
        override_price: int,
        max_ratio: float,
    ) -> None:
        super().__init__(
            message=(
                f"Override price {override_price} for SKU {sku_id} is outside "
                f"the allowed range [0, {int(base_price * max_ratio)}] "
                f"(base={base_price}, max_ratio={max_ratio})"
            ),
            error_code="PRICE_OVERRIDE_OUT_OF_RANGE",
            details={
                "sku_id": sku_id,
                "base_price": base_price,
                "override_price": override_price,
                "max_ratio": max_ratio,
            },
        )


class WalkInRefreshRecipientForbiddenError(ConflictError):
    """Walk-in orders carry an inline RecipientSnapshot without a backing
    Recipient row, so the customer-side refresh-recipient flow does not
    apply. Admins update walk-in recipient data through a separate
    admin-only path (out of MVP scope)."""

    def __init__(self, *, order_id: str) -> None:
        super().__init__(
            message=(
                f"Walk-in order {order_id} cannot refresh recipient via the "
                "self-service flow — admins must update inline data directly."
            ),
            error_code="WALK_IN_REFRESH_FORBIDDEN",
            details={"order_id": order_id},
        )
