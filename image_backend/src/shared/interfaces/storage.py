"""
Storage facade port (Hexagonal Architecture).

Defines ``IStorageFacade``, the public API of the Storage module exposed
to other bounded contexts. Encapsulates blob storage (S3) operations and
database bookkeeping behind a single protocol.

Typical usage:
    class CreateBrandHandler:
        def __init__(self, storage: IStorageFacade) -> None:
            self._storage = storage

        async def run(self) -> PresignedUploadData:
            return await self._storage.request_direct_upload(...)
"""

import uuid
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PresignedUploadData:
    """Result of a presigned upload request.

    Attributes:
        url_data: Presigned URL string (PUT) or dict with url + fields (POST).
        object_key: Full S3 key where the file will be stored.
        file_id: Database ID of the reserved ``StorageObject``, if applicable.
    """

    url_data: dict | str
    object_key: str
    file_id: uuid.UUID | None = None


class IStorageFacade(Protocol):
    """Public API of the Storage module (Facade pattern).

    Hides the internal blob storage (S3) and database (IStorageRepository)
    details behind a unified interface for other bounded contexts.
    """

    async def request_upload(
        self, module: str, entity_id: str | uuid.UUID, filename: str
    ) -> PresignedUploadData:
        """Generate a presigned POST URL for direct-to-S3 multipart upload.

        All path-prefix logic is encapsulated internally.

        Args:
            module: Owning module name (e.g. ``"catalog"``).
            entity_id: Identifier of the owning entity.
            filename: Original client filename.

        Returns:
            Presigned upload data with URL and fields.
        """
        ...

    async def request_direct_upload(
        self,
        module: str,
        entity_id: str | uuid.UUID,
        filename: str,
        content_type: str,
        expire_in: int = 300,
    ) -> PresignedUploadData:
        """Generate a presigned PUT URL for direct single-request upload.

        Args:
            module: Owning module name.
            entity_id: Identifier of the owning entity.
            filename: Original client filename.
            content_type: Expected MIME type of the upload.
            expire_in: URL validity in seconds.

        Returns:
            Presigned upload data with PUT URL.
        """
        ...

    async def reserve_upload_slot(
        self,
        module: str,
        entity_id: str | uuid.UUID,
        filename: str,
        content_type: str,
        expire_in: int = 300,
    ) -> PresignedUploadData:
        """Reserve a database slot and generate a presigned upload URL.

        Creates a ``StorageObject`` record in ``pending`` state before
        returning the presigned URL, enabling upload verification later.

        Args:
            module: Owning module name.
            entity_id: Identifier of the owning entity.
            filename: Original client filename.
            content_type: Expected MIME type of the upload.
            expire_in: URL validity in seconds.

        Returns:
            Presigned upload data including the reserved ``file_id``.
        """
        ...

    async def verify_upload(self, file_id: uuid.UUID) -> dict[str, Any]:
        """Verify that a previously reserved upload exists in S3.

        Args:
            file_id: Internal database ID of the storage object.

        Returns:
            Metadata dict for the verified object.

        Raises:
            NotFoundError: If the storage object record does not exist.
            BadRequestError: If the file is not found in S3.
        """
        ...

    async def update_object_metadata(
        self,
        file_id: uuid.UUID,
        object_key: str,
        size_bytes: int,
        content_type: str,
    ) -> None:
        """Update metadata of an existing storage object after processing.

        Args:
            file_id: Internal database ID of the storage object.
            object_key: New or confirmed S3 key.
            size_bytes: File size in bytes.
            content_type: Updated MIME type.
        """
        ...

    async def register_processed_media(
        self,
        module: str,
        entity_id: str | uuid.UUID,
        object_key: str,
        content_type: str,
        size: int,
    ) -> uuid.UUID:
        """Register a processed media file's metadata in the database.

        Args:
            module: Owning module name.
            entity_id: Identifier of the owning entity.
            object_key: Final S3 key of the processed file.
            content_type: MIME type of the processed file.
            size: File size in bytes.

        Returns:
            UUID of the newly created storage record.
        """
        ...

    async def verify_module_upload(
        self, module: str, entity_id: str | uuid.UUID, object_key: str
    ) -> dict[str, Any]:
        """Verify that a specific entity's upload exists in S3.

        Args:
            module: Owning module name.
            entity_id: Identifier of the owning entity.
            object_key: Exact S3 key to verify.

        Returns:
            Metadata dict for the verified object.
        """
        ...
