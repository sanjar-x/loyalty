"""Storage domain value objects."""

from enum import StrEnum


class StorageStatus(StrEnum):
    """Processing lifecycle of a storage object."""

    PENDING_UPLOAD = "PENDING_UPLOAD"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        return self in (StorageStatus.COMPLETED, StorageStatus.FAILED)
