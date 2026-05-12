"""Reserve an upload slot and produce a presigned S3 PUT URL (IMG-001).

Replaces the prior in-router business logic that called
``repo.add(storage_file)`` + ``uow.commit()`` straight from the
``request_upload`` FastAPI handler. Now the router only handles
HTTP framing + auth and delegates to this command.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.image.domain.entities import StorageFile
from src.modules.image.domain.interfaces import IBlobStorage, IStorageRepository
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RequestUploadCommand:
    content_type: str
    filename: str | None
    bucket_name: str
    presigned_url_ttl: int


@dataclass(frozen=True)
class RequestUploadResult:
    storage_object_id: uuid.UUID
    presigned_url: str
    expires_in: int


class RequestUploadHandler:
    """Reserve a ``storage_files`` row and return a presigned PUT URL."""

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
        self._logger = logger.bind(handler="RequestUploadHandler")

    async def handle(self, command: RequestUploadCommand) -> RequestUploadResult:
        filename = command.filename or f"upload.{command.content_type.split('/')[-1]}"

        storage_file = StorageFile.create(
            bucket_name=command.bucket_name,
            object_key="",
            content_type=command.content_type,
            filename=filename,
        )
        object_key = f"raw/{storage_file.id}/{filename}"
        storage_file.object_key = object_key

        presigned_url = await self._blob.generate_presigned_put_url(
            object_name=object_key,
            content_type=command.content_type,
            expiration=command.presigned_url_ttl,
        )

        async with self._uow:
            await self._repo.add(storage_file)
            await self._uow.commit()

        self._logger.info(
            "storage_upload_slot_reserved",
            storage_object_id=str(storage_file.id),
            object_key=object_key,
        )
        return RequestUploadResult(
            storage_object_id=storage_file.id,
            presigned_url=presigned_url,
            expires_in=command.presigned_url_ttl,
        )
