# src/modules/storage/infrastructure/repository.py
import uuid
from typing import Optional, Sequence

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.storage.domain.entities import StorageFile
from src.modules.storage.infrastructure.models import StorageObject

logger = structlog.get_logger(__name__)


class StorageObjectRepository:
    """
    Репозиторий для управления метаданными объектов S3.
    Data Mapper: маппинг между ORM-моделью StorageObject и доменной сущностью StorageFile.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._logger = logger.bind(component="storage_object_repository")

    # ------------------------------------------------------------------
    # Data Mapper: ORM ↔ Domain
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(orm: StorageObject) -> StorageFile:
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
            created_at=orm.created_at,
            last_modified_in_s3=orm.last_modified_in_s3,
        )

    @staticmethod
    def _to_orm(entity: StorageFile) -> StorageObject:
        return StorageObject(
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
            last_modified_in_s3=entity.last_modified_in_s3,
        )

    # ------------------------------------------------------------------
    # Repository methods
    # ------------------------------------------------------------------

    async def add(self, storage_file: StorageFile) -> None:
        """Добавление новой записи (версии) объекта."""
        orm = self._to_orm(storage_file)
        self._session.add(orm)

    async def update(self, storage_file: StorageFile) -> None:
        """Обновление существующей записи по ID."""
        orm = await self._session.get(StorageObject, storage_file.id)
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
        orm.last_modified_in_s3 = storage_file.last_modified_in_s3

    async def get_by_key(self, key: uuid.UUID) -> Optional[StorageFile]:
        """Получение метаданных по внутреннему UUID (используется другими модулями)."""
        orm = await self._session.get(StorageObject, key)
        return self._to_domain(orm) if orm else None

    async def get_active_by_key(
        self, bucket_name: str, object_key: str
    ) -> Optional[StorageFile]:
        """Получение актуальной версии файла по его S3 пути."""
        stmt = select(StorageObject).where(
            StorageObject.bucket_name == bucket_name,
            StorageObject.object_key == object_key,
            StorageObject.is_latest.is_(True),
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_all_versions(
        self, bucket_name: str, object_key: str
    ) -> Sequence[StorageFile]:
        """Получение истории всех версий конкретного файла."""
        stmt = (
            select(StorageObject)
            .where(
                StorageObject.bucket_name == bucket_name,
                StorageObject.object_key == object_key,
            )
            .order_by(StorageObject.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def deactivate_previous_versions(
        self, bucket_name: str, object_key: str
    ) -> None:
        """
        Инвалидация старых версий перед добавлением новой.
        Критически важно вызывать перед session.flush(), чтобы не нарушить
        уникальный индекс 'uix_storage_active_object'.
        """
        stmt = (
            update(StorageObject)
            .where(
                StorageObject.bucket_name == bucket_name,
                StorageObject.object_key == object_key,
                StorageObject.is_latest.is_(True),
            )
            .values(is_latest=False)
        )
        result = await self._session.execute(stmt)

        if result.rowcount > 0:
            self._logger.debug(
                "Старые версии файла деактивированы",
                bucket_name=bucket_name,
                object_key=object_key,
                deactivated_count=result.rowcount,
            )

    async def mark_as_deleted(self, bucket_name: str, object_key: str) -> None:
        """
        Мягкое удаление (эмуляция S3 Delete Marker).
        Делает файл недоступным как 'активный', но сохраняет запись в БД.
        """
        await self.deactivate_previous_versions(bucket_name, object_key)
        self._logger.info(
            "Файл помечен как удаленный", bucket_name=bucket_name, object_key=object_key
        )
