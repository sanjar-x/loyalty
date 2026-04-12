"""
Cart domain exceptions.

Each exception subclasses a specific shared exception from
``src/shared/exceptions.py`` to inherit the correct HTTP status code
and error envelope format.
"""

from src.shared.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
    ValidationError,
)

# ---------------------------------------------------------------------------
# Cart state errors
# ---------------------------------------------------------------------------


class CartNotFoundError(NotFoundError):
    def __init__(self, *, cart_id: str | None = None) -> None:
        super().__init__(
            message=f"Cart not found: {cart_id}" if cart_id else "Cart not found",
            error_code="CART_NOT_FOUND",
        )


class CartItemNotFoundError(NotFoundError):
    def __init__(self, *, item_id: str) -> None:
        super().__init__(
            message=f"Cart item not found: {item_id}",
            error_code="CART_ITEM_NOT_FOUND",
        )


class CartNotActiveError(ConflictError):
    def __init__(self, *, status: str) -> None:
        super().__init__(
            message=f"Cart is {status}, not active",
            error_code="CART_NOT_ACTIVE",
        )


class CartVersionConflictError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            message="Cart version conflict",
            error_code="CART_VERSION_CONFLICT",
        )


class CartFrozenForCheckoutError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            message="Cart is frozen for checkout",
            error_code="CART_FROZEN_FOR_CHECKOUT",
        )


# ---------------------------------------------------------------------------
# Checkout errors
# ---------------------------------------------------------------------------


class CheckoutSnapshotExpiredError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            message="Checkout snapshot expired",
            error_code="CHECKOUT_SNAPSHOT_EXPIRED",
        )


class CheckoutPriceChangedError(ConflictError):
    def __init__(self, *, price_diff: dict) -> None:
        super().__init__(
            message="SKU prices changed since checkout initiation",
            error_code="CHECKOUT_PRICE_CHANGED",
            details=price_diff,
        )


class DuplicateCheckoutAttemptError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            message="A pending checkout attempt already exists for this cart",
            error_code="DUPLICATE_CHECKOUT_ATTEMPT",
        )


# ---------------------------------------------------------------------------
# Item errors
# ---------------------------------------------------------------------------


class CartEmptyError(UnprocessableEntityError):
    def __init__(self) -> None:
        super().__init__(
            message="Cannot checkout empty cart",
            error_code="CART_EMPTY",
        )


class CartItemLimitExceededError(UnprocessableEntityError):
    def __init__(self, *, current: int, max_count: int) -> None:
        super().__init__(
            message=f"Cart item limit exceeded: {current}/{max_count}",
            error_code="CART_ITEM_LIMIT_EXCEEDED",
            details={"current_count": current, "max_count": max_count},
        )


class CartItemQuantityError(ValidationError):
    def __init__(self, *, quantity: int) -> None:
        super().__init__(
            message=f"Invalid quantity: {quantity}",
            error_code="CART_ITEM_QUANTITY_ERROR",
        )


class SkuNotAvailableError(UnprocessableEntityError):
    def __init__(self, *, sku_id: str) -> None:
        super().__init__(
            message=f"SKU not available: {sku_id}",
            error_code="SKU_NOT_AVAILABLE",
        )
