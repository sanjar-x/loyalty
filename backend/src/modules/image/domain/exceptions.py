"""Image module domain exceptions.

Adapted from image_backend's ``modules/storage/domain/exceptions.py``
to inherit from main backend's typed exception hierarchy
(``NotFoundError`` / ``ConflictError`` from ``src/shared/exceptions.py``)
instead of constructing ``AppException`` directly with a ``status_code``
keyword. This matches the pattern used by every other module here
(see ``favorites/domain/exceptions.py`` for reference).
"""

from src.shared.exceptions import ConflictError, NotFoundError


class StorageFileNotFoundError(NotFoundError):
    def __init__(self, *, storage_object_id: str) -> None:
        super().__init__(
            message=f"Storage file '{storage_object_id}' not found",
            error_code="STORAGE_FILE_NOT_FOUND",
            details={"storage_object_id": storage_object_id},
        )


class StorageFileAlreadyProcessedError(ConflictError):
    def __init__(self, *, storage_object_id: str) -> None:
        super().__init__(
            message=f"Storage file '{storage_object_id}' has already been processed",
            error_code="STORAGE_FILE_ALREADY_PROCESSED",
            details={"storage_object_id": storage_object_id},
        )
