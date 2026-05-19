"""Recipient domain exceptions."""

from src.shared.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)


class RecipientNotFoundError(NotFoundError):
    def __init__(self, *, recipient_id: str | None = None) -> None:
        super().__init__(
            message=(
                f"Recipient not found: {recipient_id}"
                if recipient_id
                else "Recipient not found"
            ),
            error_code="RECIPIENT_NOT_FOUND",
        )


class RecipientArchivedError(ConflictError):
    def __init__(self, *, recipient_id: str) -> None:
        super().__init__(
            message=f"Recipient is archived: {recipient_id}",
            error_code="RECIPIENT_ARCHIVED",
            details={"recipient_id": recipient_id},
        )


class InvalidRecipientFieldError(ValidationError):
    def __init__(self, *, field: str, reason: str) -> None:
        super().__init__(
            message=f"Invalid {field}: {reason}",
            error_code="RECIPIENT_INVALID_FIELD",
            details={"field": field, "reason": reason},
        )


class RecipientOwnershipError(NotFoundError):
    """Returned as 404 to leak no information about other identities' recipients."""

    def __init__(self, *, recipient_id: str) -> None:
        super().__init__(
            message=f"Recipient not found: {recipient_id}",
            error_code="RECIPIENT_NOT_FOUND",
        )
