"""Image module domain interfaces.

Declares the repository + blob-storage contracts that the infrastructure
layer must implement. The domain and application layers depend only on
these contracts, never on concrete implementations.
"""

import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from datetime import datetime
from typing import Any, Protocol

from src.modules.image.domain.entities import StorageFile


class IStorageRepository(ABC):
    """Repository contract for managing storage file metadata.

    All methods operate on ``StorageFile`` domain entities. Concrete
    implementations are responsible for mapping to/from the persistence
    model.
    """

    @abstractmethod
    async def add(self, storage_file: StorageFile) -> None:
        """Persist a new storage file record."""

    @abstractmethod
    async def update(self, storage_file: StorageFile) -> None:
        """Update an existing storage file record."""

    @abstractmethod
    async def get_active_by_key(
        self, bucket_name: str, object_key: str
    ) -> StorageFile | None:
        """Retrieve the current active version of a file by its S3 path."""

    @abstractmethod
    async def get_all_versions(
        self, bucket_name: str, object_key: str
    ) -> Sequence[StorageFile]:
        """Retrieve all versions of a file, ordered newest first."""

    @abstractmethod
    async def deactivate_previous_versions(
        self, bucket_name: str, object_key: str
    ) -> None:
        """Mark all existing versions of a file as inactive.

        Must be called before flushing a new active version to avoid
        violating the unique partial index on active objects.
        """

    @abstractmethod
    async def mark_as_deleted(self, bucket_name: str, object_key: str) -> None:
        """Soft-delete a file (analogous to an S3 delete marker).

        The record is kept in the database but becomes inactive.
        """

    @abstractmethod
    async def get_by_id(self, storage_object_id: uuid.UUID) -> StorageFile | None:
        """Retrieve a storage file by its primary key UUID."""

    @abstractmethod
    async def list_pending_expired(self, older_than: datetime) -> list[StorageFile]:
        """List files stuck in PENDING_UPLOAD status past a threshold.

        Useful for garbage-collection of uploads that were never completed.
        """


class IBlobStorage(Protocol):
    """Binary object storage port (Hexagonal Architecture).

    Application/domain code depends only on this Protocol; the
    aiobotocore-backed concrete implementation lives in the
    infrastructure layer and is wired through Dishka. All methods are
    async, stateless per-call, and safe for concurrent use.
    """

    def download_stream(
        self, object_name: str, chunk_size: int = 65536
    ) -> AsyncIterator[bytes]:
        """Yield the object contents as an async byte stream."""
        ...

    async def get_presigned_url(self, object_name: str, expiration: int = 3600) -> str:
        """Generate a time-limited GET URL for direct client download."""
        ...

    async def get_presigned_upload_url(
        self, object_name: str, expiration: int = 3600
    ) -> dict:
        """Generate a presigned POST upload URL with form fields."""
        ...

    async def generate_presigned_put_url(
        self, object_name: str, content_type: str, expiration: int = 3600
    ) -> str:
        """Generate a presigned PUT URL for direct single-request upload."""
        ...

    async def upload_stream(
        self,
        object_name: str,
        data_stream: AsyncIterator[bytes],
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload an object from an async byte stream (server-side upload)."""
        ...

    async def object_exists(self, object_name: str) -> bool:
        """Check whether an object exists in the bucket."""
        ...

    async def get_object_metadata(self, object_name: str) -> dict[str, Any]:
        """Retrieve metadata (content-type, size, etc.) for an object."""
        ...

    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: str | None = None,
    ) -> dict:
        """List objects in the bucket matching a prefix."""
        ...

    async def delete_object(self, object_name: str) -> None:
        """Delete a single object from the bucket."""
        ...

    async def delete_objects(self, object_names: list[str]) -> list[str]:
        """Delete multiple objects in a single batch request."""
        ...

    async def copy_object(self, source_name: str, dest_name: str) -> None:
        """Copy an object within the same bucket."""
        ...
