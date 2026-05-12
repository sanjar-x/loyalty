"""Import a media asset from an external URL (IMG-001, sync).

Used by admin tooling to seed product/brand catalogues from supplier
URLs. Synchronous: download → variant generation → S3 upload → DB
record — all in the request lifecycle.

The HTTP fetch + image-processing helpers (httpx download, Pillow
``build_variants``) live in infrastructure; the command takes the
already-downloaded ``raw_data`` and pre-built variants from the
router so the application layer stays infrastructure-clean
(architecture rule 3).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from src.modules.image.domain.entities import StorageFile
from src.modules.image.domain.interfaces import IBlobStorage, IStorageRepository
from src.modules.image.domain.value_objects import StorageStatus
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


async def _bytes_to_async_stream(data: bytes) -> AsyncIterator[bytes]:
    """Wrap raw bytes as a single-chunk async iterator (no infra dep)."""
    yield data


@dataclass(frozen=True)
class _VariantUpload:
    """One pre-built S3 object to upload (key + bytes)."""

    s3_key: str
    data: bytes


@dataclass(frozen=True)
class ImportExternalCommand:
    storage_object_id: uuid.UUID
    bucket_name: str
    main_key: str
    main_bytes: bytes
    variants_data: tuple[_VariantUpload, ...]
    variants_meta: list[dict]
    public_url: str
    filename: str
    source_url: str


@dataclass(frozen=True)
class ImportExternalResult:
    storage_object_id: uuid.UUID
    public_url: str
    variants_meta: list[dict]


class ImportExternalHandler:
    """Persist + S3-upload a pre-processed external image."""

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
        self._logger = logger.bind(handler="ImportExternalHandler")

    async def handle(self, command: ImportExternalCommand) -> ImportExternalResult:
        # Upload main + every variant before persisting — failed S3
        # writes raise before the DB row exists, so the row is not
        # orphaned in DB.
        await self._blob.upload_stream(
            command.main_key,
            _bytes_to_async_stream(command.main_bytes),
            "image/webp",
        )
        for variant in command.variants_data:
            await self._blob.upload_stream(
                variant.s3_key,
                _bytes_to_async_stream(variant.data),
                "image/webp",
            )

        storage_file = StorageFile(
            id=command.storage_object_id,
            bucket_name=command.bucket_name,
            object_key=command.main_key,
            content_type="image/webp",
            size_bytes=len(command.main_bytes),
            owner_module="external",
            status=StorageStatus.COMPLETED,
            url=command.public_url,
            image_variants=command.variants_meta,
            filename=command.filename,
        )

        async with self._uow:
            await self._repo.add(storage_file)
            await self._uow.commit()

        self._logger.info(
            "external_import_completed",
            storage_object_id=str(command.storage_object_id),
            source_url=command.source_url,
        )
        return ImportExternalResult(
            storage_object_id=command.storage_object_id,
            public_url=command.public_url,
            variants_meta=command.variants_meta,
        )


__all__ = [
    "ImportExternalCommand",
    "ImportExternalHandler",
    "ImportExternalResult",
    "_VariantUpload",
]
