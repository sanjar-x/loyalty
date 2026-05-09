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
    ServiceUnavailableError,
    UnprocessableEntityError,
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


class BackgroundRemovalDisabledError(ServiceUnavailableError):
    """Raised when ``BG_REMOVAL_ENABLED=False`` on the current node.

    C2.2 — surfaces as 503 (was 400) so the admin UI can render the
    correct "service temporarily unavailable" affordance and so the
    error envelope cleanly communicates that this is an infrastructure
    feature flag, not a client-data problem. The ``details.feature_flag``
    key tells the front-end exactly which env var to flip — protects
    against the gate being silently re-enabled with the same envelope
    text.

    Important invariant: even if the ``image_ml`` worker has the
    ``[bg-removal]`` extra installed, the web service still rejects
    when the flag is off — clients cannot bypass the feature flag by
    spamming the endpoint.
    """

    def __init__(self) -> None:
        super().__init__(
            message=(
                "Background removal feature is currently unavailable. "
                "Enable BG_REMOVAL_ENABLED on the web service AND ensure "
                "the image_ml worker has the [bg-removal] extra installed."
            ),
            error_code="BG_REMOVAL_DISABLED",
            details={"feature_flag": "BG_REMOVAL_ENABLED"},
        )
