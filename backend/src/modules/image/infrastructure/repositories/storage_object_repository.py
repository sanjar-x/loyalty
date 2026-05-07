"""Image module storage repository implementation.

SQLAlchemy-based implementation of :class:`IStorageRepository`. Uses
the Data Mapper pattern to translate between the
``StorageObjectModel`` ORM and the ``StorageFile`` domain entity.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.image.domain.entities import StorageFile
from src.modules.image.domain.interfaces import IStorageRepository
from src.modules.image.domain.value_objects import StorageStatus
from src.modules.image.infrastructure.models import StorageObjectModel

logger = structlog.get_logger(__name__)


class StorageObjectRepository(IStorageRepository):
    """Repository for managing S3 object metadata via SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._logger = logger.bind(component="storage_object_repository")

    @staticmethod
    def _to_domain(orm: StorageObjectModel) -> StorageFile:
        return StorageFile(
            id=orm.id,
            bucket_name=orm.bucket_name,
            object_key=orm.object_key,
            content_type=orm.content_type,
            size_bytes=orm.size_bytes,
            is_latest=orm.is_latest,
            owner_module=orm.owner_module,
            version_id=orm.version_id,
            etag=orm.etag,
            content_encoding=orm.content_encoding,
            cache_control=orm.cache_control,
            status=orm.status,
            url=orm.url,
            image_variants=orm.image_variants,
            filename=orm.filename,
            created_at=orm.created_at,
            last_modified_in_s3=orm.last_modified_in_s3,
        )

    @staticmethod
    def _to_orm(entity: StorageFile) -> StorageObjectModel:
        return StorageObjectModel(
            id=entity.id,
            bucket_name=entity.bucket_name,
            object_key=entity.object_key,
            content_type=entity.content_type,
            size_bytes=entity.size_bytes,
            is_latest=entity.is_latest,
            owner_module=entity.owner_module,
            version_id=entity.version_id,
            etag=entity.etag,
            content_encoding=entity.content_encoding,
            cache_control=entity.cache_control,
            status=entity.status,
            url=entity.url,
            image_variants=entity.image_variants,
            filename=entity.filename,
            last_modified_in_s3=entity.last_modified_in_s3,
        )

    async def add(self, storage_file: StorageFile) -> None:
        self._session.add(self._to_orm(storage_file))

    async def update(self, storage_file: StorageFile) -> None:
        orm = await self._session.get(StorageObjectModel, storage_file.id)
        if orm is None:
            return
        orm.object_key = storage_file.object_key
        orm.content_type = storage_file.content_type
        orm.size_bytes = storage_file.size_bytes
        orm.is_latest = storage_file.is_latest
        orm.owner_module = storage_file.owner_module
        orm.version_id = storage_file.version_id
        orm.etag = storage_file.etag
        orm.content_encoding = storage_file.content_encoding
        orm.cache_control = storage_file.cache_control
        orm.status = storage_file.status
        orm.url = storage_file.url
        orm.image_variants = storage_file.image_variants
        orm.filename = storage_file.filename
        orm.last_modified_in_s3 = storage_file.last_modified_in_s3

    async def get_active_by_key(
        self, bucket_name: str, object_key: str
    ) -> StorageFile | None:
        stmt = select(StorageObjectModel).where(
            StorageObjectModel.bucket_name == bucket_name,
            StorageObjectModel.object_key == object_key,
            StorageObjectModel.is_latest.is_(True),
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_all_versions(
        self, bucket_name: str, object_key: str
    ) -> Sequence[StorageFile]:
        stmt = (
            select(StorageObjectModel)
            .where(
                StorageObjectModel.bucket_name == bucket_name,
                StorageObjectModel.object_key == object_key,
            )
            .order_by(StorageObjectModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def deactivate_previous_versions(
        self, bucket_name: str, object_key: str
    ) -> None:
        stmt = (
            update(StorageObjectModel)
            .where(
                StorageObjectModel.bucket_name == bucket_name,
                StorageObjectModel.object_key == object_key,
                StorageObjectModel.is_latest.is_(True),
            )
            .values(is_latest=False)
        )
        result = await self._session.execute(stmt)
        if result.rowcount > 0:
            self._logger.debug(
                "Previous file versions deactivated",
                bucket_name=bucket_name,
                object_key=object_key,
                deactivated_count=result.rowcount,
            )

    async def mark_as_deleted(self, bucket_name: str, object_key: str) -> None:
        await self.deactivate_previous_versions(bucket_name, object_key)
        self._logger.info(
            "File marked as deleted", bucket_name=bucket_name, object_key=object_key
        )

    async def get_by_id(self, storage_object_id: uuid.UUID) -> StorageFile | None:
        orm = await self._session.get(StorageObjectModel, storage_object_id)
        return self._to_domain(orm) if orm else None

    async def list_pending_expired(self, older_than: datetime) -> list[StorageFile]:
        stmt = select(StorageObjectModel).where(
            StorageObjectModel.status == StorageStatus.PENDING_UPLOAD.value,
            StorageObjectModel.created_at < older_than,
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]
