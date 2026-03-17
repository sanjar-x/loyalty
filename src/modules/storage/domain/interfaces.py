"""Storage domain interfaces.

Declares the repository protocol that the infrastructure layer must
implement. The domain and application layers depend only on this
protocol, never on concrete implementations.
"""

import uuid
from collections.abc import Sequence
from typing import Protocol

from src.modules.storage.domain.entities import StorageFile


class IStorageRepository(Protocol):
    """Repository contract for managing storage file metadata.

    All methods operate on ``StorageFile`` domain entities. Concrete
    implementations are responsible for mapping to/from the persistence
    model.
    """

    async def add(self, storage_file: StorageFile) -> None:
        """Persist a new storage file record.

        Args:
            storage_file: The domain entity to persist.
        """
        ...

    async def update(self, storage_file: StorageFile) -> None:
        """Update an existing storage file record.

        Args:
            storage_file: The domain entity with updated fields.
        """
        ...

    async def get_by_key(self, key: uuid.UUID) -> StorageFile | None:
        """Retrieve a storage file by its internal UUID.

        Args:
            key: The internal identifier of the storage file.

        Returns:
            The matching ``StorageFile``, or ``None`` if not found.
        """
        ...

    async def get_active_by_key(
        self, bucket_name: str, object_key: str
    ) -> StorageFile | None:
        """Retrieve the current active version of a file by its S3 path.

        Args:
            bucket_name: The S3 bucket name.
            object_key: The full object key within the bucket.

        Returns:
            The active ``StorageFile``, or ``None`` if not found.
        """
        ...

    async def get_all_versions(
        self, bucket_name: str, object_key: str
    ) -> Sequence[StorageFile]:
        """Retrieve all versions of a file, ordered newest first.

        Args:
            bucket_name: The S3 bucket name.
            object_key: The full object key within the bucket.

        Returns:
            A sequence of ``StorageFile`` entities for every version.
        """
        ...

    async def deactivate_previous_versions(
        self, bucket_name: str, object_key: str
    ) -> None:
        """Mark all existing versions of a file as inactive.

        Must be called before flushing a new active version to avoid
        violating the unique partial index on active objects.

        Args:
            bucket_name: The S3 bucket name.
            object_key: The full object key within the bucket.
        """
        ...

    async def mark_as_deleted(self, bucket_name: str, object_key: str) -> None:
        """Soft-delete a file (analogous to an S3 delete marker).

        The record is kept in the database but becomes inactive.

        Args:
            bucket_name: The S3 bucket name.
            object_key: The full object key within the bucket.
        """
        ...
