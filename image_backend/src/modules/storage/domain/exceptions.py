"""Storage domain exceptions.

Custom exceptions for the storage bounded context.  Each class extends
the shared ``AppException`` base so that the presentation layer can
map them to the correct HTTP status automatically.
"""

from src.shared.exceptions import AppException


class StorageFileNotFoundError(AppException):
    """Raised when a storage file cannot be found (HTTP 404)."""

    def __init__(self, storage_object_id: str) -> None:
        super().__init__(
            message=f"Storage file '{storage_object_id}' not found",
            status_code=404,
            error_code="STORAGE_FILE_NOT_FOUND",
            details={"storage_object_id": storage_object_id},
        )


class StorageFileAlreadyProcessedError(AppException):
    """Raised when a file has already reached a terminal state (HTTP 409)."""

    def __init__(self, storage_object_id: str) -> None:
        super().__init__(
            message=f"Storage file '{storage_object_id}' has already been processed",
            status_code=409,
            error_code="STORAGE_FILE_ALREADY_PROCESSED",
            details={"storage_object_id": storage_object_id},
        )
