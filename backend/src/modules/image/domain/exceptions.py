"""Image module domain exceptions.

Adapted from image_backend's ``modules/storage/domain/exceptions.py``
to inherit from main backend's typed exception hierarchy
(``NotFoundError`` / ``ConflictError`` from ``src/shared/exceptions.py``)
instead of constructing ``AppException`` directly with a ``status_code``
keyword. This matches the pattern used by every other module here
(see ``favorites/domain/exceptions.py`` for reference).
"""

from src.shared.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
    ValidationError,
)


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


class StorageFileNotReadyError(UnprocessableEntityError):
    """Raised when a derivation is requested against a non-COMPLETED parent.

    Background removal needs the public processed bytes, so the parent
    must have finished its own ``process_image_task``. Returning 422
    (instead of 409) signals the client to retry once the parent
    settles.
    """

    def __init__(self, *, storage_object_id: str, status: str) -> None:
        super().__init__(
            message=(
                f"Storage file '{storage_object_id}' is not ready "
                f"(status={status}); wait for processing to complete."
            ),
            error_code="STORAGE_FILE_NOT_READY",
            details={"storage_object_id": storage_object_id, "status": status},
        )


class BackgroundRemovalDisabledError(ValidationError):
    """Raised when ``BG_REMOVAL_ENABLED=False`` on the current node.

    Surfaces as 400 with a precise error code so the admin UI can
    hide / disable the action proactively rather than relying on a
    blind 500.
    """

    def __init__(self) -> None:
        super().__init__(
            message=(
                "Background removal is disabled on this deployment. "
                "Enable BG_REMOVAL_ENABLED on the image_ml worker."
            ),
            error_code="BACKGROUND_REMOVAL_DISABLED",
            details={},
        )
