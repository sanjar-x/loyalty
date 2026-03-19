"""Storage domain entities.

Defines the core domain entity for files stored in an S3-compatible
object storage. This entity is a pure attrs dataclass with no
infrastructure dependencies.
"""

import uuid
from datetime import datetime

from attr import dataclass


@dataclass
class StorageFile:
    """Domain entity representing a file in the object storage.

    Tracks metadata about a single version of an object stored in an
    S3-compatible bucket, including its location, content characteristics,
    versioning state, and ownership.

    Attributes:
        id: Internal unique identifier.
        bucket_name: S3 bucket where the object resides.
        object_key: Full path to the object within the bucket.
        content_type: MIME type of the file (e.g. ``image/webp``).
        size_bytes: File size in bytes.
        is_latest: Whether this is the current active version.
        owner_module: Name of the owning bounded-context module.
        version_id: S3 version identifier (when bucket versioning is enabled).
        etag: MD5 hash returned by S3 for integrity checks.
        content_encoding: HTTP ``Content-Encoding`` header value.
        cache_control: HTTP ``Cache-Control`` header value.
        created_at: Timestamp when the record was created.
        last_modified_in_s3: Timestamp of the last modification on the S3 side.
    """

    id: uuid.UUID
    bucket_name: str
    object_key: str
    content_type: str
    size_bytes: int = 0
    is_latest: bool = True
    owner_module: str | None = None
    version_id: str | None = None
    etag: str | None = None
    content_encoding: str | None = None
    cache_control: str | None = None
    created_at: datetime | None = None
    last_modified_in_s3: datetime | None = None

    @classmethod
    def create(
        cls,
        bucket_name: str,
        object_key: str,
        content_type: str,
        size_bytes: int = 0,
        owner_module: str | None = None,
    ) -> StorageFile:
        """Create a new ``StorageFile`` with a generated UUID.

        Factory method that produces a fresh entity ready to be persisted.
        Uses UUID v7 when available, falling back to UUID v4.

        Args:
            bucket_name: Target S3 bucket name.
            object_key: Full path within the bucket.
            content_type: MIME type of the file.
            size_bytes: File size in bytes. Defaults to 0.
            owner_module: Name of the module that owns this file.

        Returns:
            A new ``StorageFile`` instance with a generated ``id``.
        """
        return cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            bucket_name=bucket_name,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            owner_module=owner_module,
        )
