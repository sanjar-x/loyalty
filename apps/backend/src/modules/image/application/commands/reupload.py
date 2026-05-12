"""Reupload an existing storage file with a new presigned PUT URL (IMG-001).

Used when an admin needs to replace the underlying image but keep the
same ``storage_object_id`` (and the public URL it minted), e.g. after
a content correction. The status is rewound to ``PENDING_UPLOAD`` and
a fresh presigned URL is generated.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.image.domain.exceptions import StorageFileNotFoundError
from src.modules.image.domain.interfaces import IBlobStorage, IStorageRepository
from src.modules.image.domain.value_objects import StorageStatus
from shared.exceptions import ConflictError
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ReuploadCommand:
    storage_object_id: uuid.UUID
    content_type: str
    filename: str | None
    presigned_url_ttl: int


@dataclass(frozen=True)
class ReuploadResult:
    storage_object_id: uuid.UUID
    presigned_url: str
    expires_in: int


class ReuploadHandler:
    """Generate a fresh presigned PUT URL for an existing storage file."""

    def __init__(
        self,
        repo: IStorageRepository,
        blob_storage: IBlobStorage,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._blob = blob_storage
        self._uow = uow
        self._logger = logger.bind(handler="ReuploadHandler")

    async def handle(self, command: ReuploadCommand) -> ReuploadResult:
        storage_file = await self._repo.get_by_id(command.storage_object_id)
        if not storage_file:
            raise StorageFileNotFoundError(
                storage_object_id=str(command.storage_object_id)
            )

        if storage_file.status == StorageStatus.PROCESSING:
            raise ConflictError(
                message="Cannot reupload while image is being processed.",
                error_code="STORAGE_FILE_PROCESSING_IN_PROGRESS",
                details={"storage_object_id": str(command.storage_object_id)},
            )

        filename = command.filename or f"upload.{command.content_type.split('/')[-1]}"
        object_key = f"raw/{command.storage_object_id}/{filename}"

        presigned_url = await self._blob.generate_presigned_put_url(
            object_name=object_key,
            content_type=command.content_type,
            expiration=command.presigned_url_ttl,
        )

        storage_file.object_key = object_key
        storage_file.content_type = command.content_type
        storage_file.filename = filename
        storage_file.status = StorageStatus.PENDING_UPLOAD

        async with self._uow:
            await self._repo.update(storage_file)
            await self._uow.commit()

        self._logger.info(
            "storage_file_reuploaded",
            storage_object_id=str(command.storage_object_id),
            object_key=object_key,
        )
        return ReuploadResult(
            storage_object_id=command.storage_object_id,
            presigned_url=presigned_url,
            expires_in=command.presigned_url_ttl,
        )
