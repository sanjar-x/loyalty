"""Passport domain exceptions."""

from __future__ import annotations

from src.shared.exceptions import (
    NotFoundError,
    UnprocessableEntityError,
    ValidationError,
)


class InvalidCustomsDataError(ValidationError):
    """Customs data field failed format-level validation (400)."""

    def __init__(self, *, field: str, reason: str) -> None:
        super().__init__(
            message=f"Invalid customs field '{field}': {reason}",
            error_code="PASSPORT_INVALID_CUSTOMS_DATA",
            details={"field": field, "reason": reason},
        )


class InvalidPassportFieldError(ValidationError):
    """Generic passport-field validation error (full name etc.) (400)."""

    def __init__(self, *, field: str, reason: str) -> None:
        super().__init__(
            message=f"Invalid passport field '{field}': {reason}",
            error_code="PASSPORT_INVALID_FIELD",
            details={"field": field, "reason": reason},
        )


class PassportNotFoundError(NotFoundError):
    """Passport with the given id was not found (404)."""

    def __init__(self, *, passport_id: str) -> None:
        super().__init__(
            message=f"Passport {passport_id} not found",
            error_code="PASSPORT_NOT_FOUND",
            details={"passport_id": passport_id},
        )


class PassportArchivedError(UnprocessableEntityError):
    """Cannot mutate an archived passport (422)."""

    def __init__(self, *, passport_id: str) -> None:
        super().__init__(
            message=f"Passport {passport_id} is archived and cannot be modified",
            error_code="PASSPORT_ARCHIVED",
            details={"passport_id": passport_id},
        )


class PassportOwnershipMismatchError(UnprocessableEntityError):
    """Passport does not belong to the requesting identity (422).

    Surfaced from Order handlers (cross-border invariant lookup) when a
    customer tries to attach someone else's passport_id.
    """

    def __init__(self, *, passport_id: str) -> None:
        super().__init__(
            message="Passport does not belong to this customer",
            error_code="PASSPORT_OWNERSHIP_MISMATCH",
            details={"passport_id": passport_id},
        )
