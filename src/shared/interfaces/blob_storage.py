"""
Binary object storage port (Hexagonal Architecture).

Defines the ``IBlobStorage`` protocol that the application layer depends on
for all S3-compatible operations. The concrete implementation (aiobotocore)
lives in the infrastructure layer and is injected via Dishka.

Typical usage:
    class MyHandler:
        def __init__(self, blob: IBlobStorage) -> None:
            self._blob = blob

        async def run(self) -> str:
            return await self._blob.get_presigned_url("key")
"""

from collections.abc import AsyncIterator
from typing import Any, Protocol


class IBlobStorage(Protocol):
    """Contract for binary (object) storage operations.

    All methods are async and designed for S3-compatible backends.
    Implementations must be stateless per-call and safe for concurrent use.
    """

    def download_stream(
        self, object_name: str, chunk_size: int = 65536
    ) -> AsyncIterator[bytes]:
        """Yield the object contents as an async byte stream.

        Args:
            object_name: Full key of the object in the bucket.
            chunk_size: Maximum bytes per yielded chunk.

        Returns:
            Async iterator yielding byte chunks.
        """
        ...

    async def get_presigned_url(self, object_name: str, expiration: int = 3600) -> str:
        """Generate a time-limited GET URL for direct client download.

        Args:
            object_name: Full key of the object in the bucket.
            expiration: URL validity in seconds.

        Returns:
            Presigned URL string.
        """
        ...

    async def get_presigned_upload_url(
        self, object_name: str, expiration: int = 3600
    ) -> dict:
        """Generate a presigned POST upload URL with form fields.

        Args:
            object_name: Target key for the uploaded object.
            expiration: URL validity in seconds.

        Returns:
            Dict with ``url`` and ``fields`` for a multipart form POST.
        """
        ...

    async def generate_presigned_put_url(
        self, object_name: str, content_type: str, expiration: int = 3600
    ) -> str:
        """Generate a presigned PUT URL for direct single-request upload.

        Args:
            object_name: Target key for the uploaded object.
            content_type: MIME type the client must send in the PUT request.
            expiration: URL validity in seconds.

        Returns:
            Presigned URL string.
        """
        ...

    async def upload_stream(
        self,
        object_name: str,
        data_stream: AsyncIterator[bytes],
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload an object from an async byte stream (server-side upload).

        Args:
            object_name: Target key for the uploaded object.
            data_stream: Async iterator yielding byte chunks.
            content_type: MIME type stored as object metadata.

        Returns:
            The final object key after successful upload.
        """
        ...

    async def object_exists(self, object_name: str) -> bool:
        """Check whether an object exists in the bucket.

        Args:
            object_name: Full key to check.

        Returns:
            True if the object exists, False otherwise.
        """
        ...

    async def get_object_metadata(self, object_name: str) -> dict[str, Any]:
        """Retrieve metadata (content-type, size, etc.) for an object.

        Args:
            object_name: Full key of the object.

        Returns:
            Dict of metadata key-value pairs.
        """
        ...

    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: str | None = None,
    ) -> dict:
        """List objects in the bucket matching a prefix.

        Args:
            prefix: Key prefix filter.
            limit: Maximum number of keys to return.
            continuation_token: Pagination cursor from a previous call.

        Returns:
            Dict with ``objects`` (list of keys) and ``continuation_token``.
        """
        ...

    async def delete_object(self, object_name: str) -> None:
        """Delete a single object from the bucket.

        Args:
            object_name: Full key of the object to delete.
        """
        ...

    async def delete_objects(self, object_names: list[str]) -> list[str]:
        """Delete multiple objects in a single batch request.

        Args:
            object_names: List of keys to delete.

        Returns:
            List of keys that were successfully deleted.
        """
        ...

    async def copy_object(self, source_name: str, dest_name: str) -> None:
        """Copy an object within the same bucket.

        Args:
            source_name: Key of the source object.
            dest_name: Key for the destination copy.
        """
        ...
