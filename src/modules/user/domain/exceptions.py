"""User domain exceptions.

Defines domain-specific exceptions for the User bounded context.
"""

import uuid

from src.shared.exceptions import NotFoundError


class UserNotFoundError(NotFoundError):
    """Raised when a user cannot be found by the given identifier.

    .. deprecated::
        Use :class:`CustomerNotFoundError` or :class:`StaffMemberNotFoundError` instead.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable error code for API consumers.
        details: Additional context including the requested user ID.
    """

    def __init__(self, user_id: uuid.UUID | str) -> None:
        """Initialize the error with the missing user's ID.

        Args:
            user_id: The identifier of the user that was not found.
        """
        super().__init__(
            message=f"User with ID {user_id} not found",
            error_code="USER_NOT_FOUND",
            details={"user_id": str(user_id)},
        )


class CustomerNotFoundError(NotFoundError):
    """Raised when a customer cannot be found by the given identifier.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable error code for API consumers.
        details: Additional context including the requested customer ID.
    """

    def __init__(self, customer_id: uuid.UUID | str) -> None:
        """Initialize the error with the missing customer's ID.

        Args:
            customer_id: The identifier of the customer that was not found.
        """
        super().__init__(
            message=f"Customer with ID {customer_id} not found",
            error_code="CUSTOMER_NOT_FOUND",
            details={"customer_id": str(customer_id)},
        )


class StaffMemberNotFoundError(NotFoundError):
    """Raised when a staff member cannot be found by the given identifier.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable error code for API consumers.
        details: Additional context including the requested staff member ID.
    """

    def __init__(self, staff_id: uuid.UUID | str) -> None:
        """Initialize the error with the missing staff member's ID.

        Args:
            staff_id: The identifier of the staff member that was not found.
        """
        super().__init__(
            message=f"Staff member with ID {staff_id} not found",
            error_code="STAFF_MEMBER_NOT_FOUND",
            details={"staff_id": str(staff_id)},
        )
