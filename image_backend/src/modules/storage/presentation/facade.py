"""Storage facade (application service).

Provides a high-level API for other modules to interact with the
Storage bounded context. Encapsulates presigned URL generation,
upload verification, file registration, and metadata updates behind
the ``IStorageFacade`` interface.
"""

import uuid
from typing import Any

from src.modules.storage.domain.entities import StorageFile
from src.modules.storage.domain.interfaces import IStorageRepository
from src.shared.exceptions import ValidationError
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.storage import IStorageFacade, PresignedUploadData
from src.shared.interfaces.uow import IUnitOfWork


class StorageFacade(IStorageFacade):
    """Facade that orchestrates blob storage and metadata operations.

    Acts as the single entry point for all storage-related use cases,
    coordinating between the S3 blob storage service, the file metadata
    repository, and the unit of work.

    Args:
        blob_storage: S3-compatible blob storage service.
        storage_repo: Repository for file metadata persistence.
        uow: Unit of Work for transactional consistency.
        settings: Storage configuration (bucket name, etc.).
        logger: Structured logger instance.
    """

    def __init__(
        self,
        blob_storage: IBlobStorage,
        storage_repo: IStorageRepository,
        uow: IUnitOfWork,
        settings: IStorageConfig,
        logger: ILogger,
    ):
        self._blob_storage: IBlobStorage = blob_storage
        self._storage_repo: IStorageRepository = storage_repo
        self._uow: IUnitOfWork = uow
        self._settings: IStorageConfig = settings
        self._logger = logger.bind(component="StorageFacade")

    async def request_upload(
        self, module: str, entity_id: str | uuid.UUID, filename: str
    ) -> PresignedUploadData:
        """Generate a presigned POST URL for uploading a file.

        The file is placed under a temporary prefix until processing
        is complete.

        Args:
            module: Name of the requesting module.
            entity_id: Identifier of the owning entity.
            filename: Original filename (used to determine extension).

        Returns:
            Presigned upload data containing the URL and object key.
        """
        file_ext = filename.split(".")[-1] if "." in filename else "bin"

        object_key = f"temp/{module}/{entity_id}/upload.{file_ext}"

        url_data = await self._blob_storage.get_presigned_upload_url(
            object_name=object_key, expiration=3600
        )

        self._logger.info("Presigned URL generated", object_key=object_key)

        return PresignedUploadData(url_data=url_data, object_key=object_key)

    async def request_direct_upload(
        self,
        module: str,
        entity_id: str | uuid.UUID,
        filename: str,
        content_type: str,
        expire_in: int = 300,
    ) -> PresignedUploadData:
        """Generate a presigned PUT URL for direct (single-request) upload.

        The file is placed under the ``raw_uploads/`` prefix.

        Args:
            module: Name of the requesting module.
            entity_id: Identifier of the owning entity.
            filename: Original filename (used to determine extension).
            content_type: Required MIME type for the upload.
            expire_in: URL validity duration in seconds. Defaults to 300.

        Returns:
            Presigned upload data containing the PUT URL and object key.
        """
        file_ext = filename.split(".")[-1] if "." in filename else "bin"
        object_key = f"raw_uploads/{module}/{entity_id}/upload_raw.{file_ext}"

        url_str = await self._blob_storage.generate_presigned_put_url(
            object_name=object_key, content_type=content_type, expiration=expire_in
        )

        self._logger.info("Presigned PUT URL generated", object_key=object_key)
        return PresignedUploadData(url_data=url_str, object_key=object_key)

    async def register_processed_media(
        self,
        module: str,
        entity_id: str | uuid.UUID,
        object_key: str,
        content_type: str,
        size: int,
    ) -> uuid.UUID:
        """Register a fully processed media file in the storage registry.

        Creates a new ``StorageFile`` record and persists it within a
        unit of work transaction.

        Args:
            module: Name of the owning module.
            entity_id: Identifier of the owning entity.
            object_key: Final S3 object key of the processed file.
            content_type: MIME type of the processed file.
            size: File size in bytes.

        Returns:
            The UUID of the newly created ``StorageFile``.
        """
        storage_file = StorageFile.create(
            bucket_name=self._settings.S3_BUCKET_NAME,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size,
            owner_module=module,
        )

        async with self._uow:
            await self._storage_repo.add(storage_file)
            await self._uow.commit()

        self._logger.info("File registered", object_key=str(storage_file.id))
        return storage_file.id

    async def _check_file_in_s3(self, object_key: str) -> dict[str, Any]:
        """Verify that a file exists in S3 and return its metadata.

        Args:
            object_key: The S3 object key to check.

        Returns:
            A metadata dict enriched with the ``object_key`` field.

        Raises:
            ValidationError: If the file is not found in S3.
        """
        metadata = await self._blob_storage.get_object_metadata(object_key)
        if not metadata:
            self._logger.error("File not found in S3", object_key=object_key)
            raise ValidationError(message="File was not uploaded to storage.")
        metadata["object_key"] = object_key
        return metadata

    async def verify_module_upload(
        self, module: str, entity_id: str | uuid.UUID, object_key: str
    ) -> dict[str, Any]:
        """Verify that a module's upload exists in S3.

        Args:
            module: Name of the requesting module.
            entity_id: Identifier of the owning entity.
            object_key: The S3 object key to verify.

        Returns:
            S3 metadata for the uploaded object.

        Raises:
            ValidationError: If the file is not found in S3.
        """
        return await self._check_file_in_s3(object_key)

    async def reserve_upload_slot(
        self,
        module: str,
        entity_id: str | uuid.UUID,
        filename: str,
        content_type: str,
        expire_in: int = 300,
    ) -> PresignedUploadData:
        """Reserve an upload slot: generate a PUT URL and pre-register the file.

        Unlike ``request_direct_upload``, this method also persists a
        ``StorageFile`` record immediately so the file ID is available
        before the actual upload completes.

        Args:
            module: Name of the requesting module.
            entity_id: Identifier of the owning entity.
            filename: Original filename (used to determine extension).
            content_type: Required MIME type for the upload.
            expire_in: URL validity duration in seconds. Defaults to 300.

        Returns:
            Presigned upload data including the PUT URL, object key,
            and the pre-registered file ID.
        """
        file_ext = filename.split(".")[-1] if "." in filename else "bin"
        object_key = f"raw_uploads/{module}/{entity_id}/upload_raw.{file_ext}"

        url_str = await self._blob_storage.generate_presigned_put_url(
            object_name=object_key, content_type=content_type, expiration=expire_in
        )

        storage_file = StorageFile.create(
            bucket_name=self._settings.S3_BUCKET_NAME,
            object_key=object_key,
            content_type=content_type,
            owner_module=module,
        )

        async with self._uow:
            await self._storage_repo.add(storage_file)
            await self._uow.commit()

        self._logger.info(
            "Upload slot reserved",
            object_key=object_key,
            file_id=str(storage_file.id),
        )

        return PresignedUploadData(
            url_data=url_str,
            object_key=object_key,
            file_id=storage_file.id,
        )

    async def verify_upload(self, file_id: uuid.UUID) -> dict[str, Any]:
        """Verify that a previously reserved upload has been completed.

        Looks up the ``StorageFile`` record by ID, then checks S3 for
        the actual object.

        Args:
            file_id: The UUID of the pre-registered storage file.

        Returns:
            S3 metadata for the uploaded object.

        Raises:
            ValidationError: If the file record is not found or the
                file was not uploaded to S3.
        """
        async with self._uow:
            storage_file = await self._storage_repo.get_by_key(file_id)

        if not storage_file:
            raise ValidationError(message="File record not found.")

        return await self._check_file_in_s3(storage_file.object_key)

    async def update_object_metadata(
        self,
        file_id: uuid.UUID,
        object_key: str,
        size_bytes: int,
        content_type: str,
    ) -> None:
        """Update metadata for an existing storage file record.

        Typically called after media processing has finalized the file
        at a new location or with updated characteristics.

        Args:
            file_id: The UUID of the storage file to update.
            object_key: The new (or unchanged) S3 object key.
            size_bytes: Updated file size in bytes.
            content_type: Updated MIME type.

        Raises:
            ValidationError: If the file record is not found.
        """
        async with self._uow:
            storage_file = await self._storage_repo.get_by_key(file_id)
            if not storage_file:
                raise ValidationError(message="File record not found.")

            storage_file.object_key = object_key
            storage_file.size_bytes = size_bytes
            storage_file.content_type = content_type

            await self._storage_repo.update(storage_file)
            await self._uow.commit()

        self._logger.info("File metadata updated", file_id=str(file_id))
