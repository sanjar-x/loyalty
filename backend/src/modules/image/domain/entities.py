"""Image module domain entities.

Defines the core domain entity for files stored in an S3-compatible
object storage. Inherits :class:`AggregateRoot` per main-backend
convention so the aggregate can buffer domain events for the
Transactional Outbox; the original image_backend implementation was
a plain attrs dataclass without events.

Pure attrs dataclass with no infrastructure dependencies (Rule 6 —
domain layer must not import from application/infrastructure/
presentation).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from attr import define

from src.modules.image.domain.value_objects import DerivationKind, StorageStatus
from src.shared.interfaces.entities import AggregateRoot


def _generate_id() -> uuid.UUID:
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


@define
class StorageFile(AggregateRoot):
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
        status: Processing lifecycle status of the storage object.
        url: Public URL of the processed file (set after processing completes).
        image_variants: List of generated image variant metadata dicts.
        filename: Original filename of the uploaded file.
        parent_storage_object_id: Set when this row is a *derivation*
            (e.g. background-removed copy) of another storage object —
            ``None`` for plain uploads. Together with
            ``derivation_kind`` it gives the admin UI a "revert to
            original" hand-off without a fresh upload.
        derivation_kind: Discriminator for the kind of transformation
            applied (``BG_REMOVED``, future ``UPSCALED``, ...). Always
            set when ``parent_storage_object_id`` is set; mutually
            exclusive with original-upload rows.
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
    status: StorageStatus = StorageStatus.PENDING_UPLOAD
    url: str | None = None
    image_variants: list[dict] | None = None
    filename: str | None = None
    parent_storage_object_id: uuid.UUID | None = None
    derivation_kind: DerivationKind | None = None
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
        filename: str | None = None,
        parent_storage_object_id: uuid.UUID | None = None,
        derivation_kind: DerivationKind | None = None,
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
            filename: Original filename of the uploaded file.
            parent_storage_object_id: Parent storage object when this
                file is a derivation; ``None`` for plain uploads.
            derivation_kind: Required iff ``parent_storage_object_id``
                is provided.

        Returns:
            A new ``StorageFile`` instance with a generated ``id``.

        Raises:
            ValueError: If exactly one of ``parent_storage_object_id``
                / ``derivation_kind`` is provided. Both fields must
                travel together — a derivation without a kind, or a
                kind without a parent, is meaningless.
        """
        if (parent_storage_object_id is None) != (derivation_kind is None):
            raise ValueError(
                "parent_storage_object_id and derivation_kind must be "
                "provided together (or both omitted)."
            )
        return cls(
            id=_generate_id(),
            bucket_name=bucket_name,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            owner_module=owner_module,
            filename=filename,
            parent_storage_object_id=parent_storage_object_id,
            derivation_kind=derivation_kind,
        )
