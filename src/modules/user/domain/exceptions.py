# src/modules/user/domain/exceptions.py
import uuid

from src.shared.exceptions import NotFoundError


class UserNotFoundError(NotFoundError):
    def __init__(self, user_id: uuid.UUID | str) -> None:
        super().__init__(
            message=f"User with ID {user_id} not found",
            error_code="USER_NOT_FOUND",
            details={"user_id": str(user_id)},
        )
