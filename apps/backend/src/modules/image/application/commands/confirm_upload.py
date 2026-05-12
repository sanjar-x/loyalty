"""Confirm S3 upload completion + transition to PROCESSING (IMG-001).

After the admin's browser successfully PUTs the file to S3, this
command verifies presence + size and transitions the storage row to
``PROCESSING``. The variant-generation TaskIQ task is dispatched by
the router after the handler returns — keeping the command pure of
infrastructure dependencies (architecture rule 3 forbids
application/commands → infrastructure imports).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.image.domain.exceptions import (
    StorageFileAlreadyProcessedError,
    StorageFileNotFoundError,
)
from src.modules.image.domain.interfaces import IBlobStorage, IStorageRepository
from src.modules.image.domain.value_objects import StorageStatus
from shared.exceptions import UnprocessableEntityError
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ConfirmUploadCommand:
    storage_object_id: uuid.UUID
    max_file_size: int


class ConfirmUploadHandler:
    """Verify S3 upload + transition to PROCESSING.

    Returns when the DB row is at ``PROCESSING``. The router enqueues
    the variant-generation task **after** this returns so the worker
    cannot race the COMMIT.
    """

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
        self._logger = logger.bind(handler="ConfirmUploadHandler")

    async def handle(self, command: ConfirmUploadCommand) -> None:
        storage_file = await self._repo.get_by_id(command.storage_object_id)
        if not storage_file:
            raise StorageFileNotFoundError(
                storage_object_id=str(command.storage_object_id)
            )

        if storage_file.status != StorageStatus.PENDING_UPLOAD:
            raise StorageFileAlreadyProcessedError(
                storage_object_id=str(command.storage_object_id)
            )

        metadata = await self._blob.get_object_metadata(storage_file.object_key)
        if not metadata:
            raise UnprocessableEntityError(
                message="File not found in S3. Upload may not have completed.",
                error_code="STORAGE_OBJECT_NOT_UPLOADED",
                details={"storage_object_id": str(command.storage_object_id)},
            )

        file_size = metadata.get("content_length", 0)
        if file_size > command.max_file_size:
            raise UnprocessableEntityError(
                message=(
                    f"File too large: {file_size} bytes (max {command.max_file_size})."
                ),
                error_code="STORAGE_OBJECT_TOO_LARGE",
                details={
                    "storage_object_id": str(command.storage_object_id),
                    "size": file_size,
                    "max": command.max_file_size,
                },
            )

        storage_file.status = StorageStatus.PROCESSING

        async with self._uow:
            await self._repo.update(storage_file)
            await self._uow.commit()

        self._logger.info(
            "storage_upload_confirmed",
            storage_object_id=str(command.storage_object_id),
            size=file_size,
        )
