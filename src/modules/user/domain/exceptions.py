"""User domain exceptions.

Defines domain-specific exceptions for the User bounded context.
"""

import uuid

from src.shared.exceptions import NotFoundError


class UserNotFoundError(NotFoundError):
    """Raised when a user cannot be found by the given identifier.

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
