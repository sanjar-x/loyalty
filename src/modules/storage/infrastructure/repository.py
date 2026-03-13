# src\modules\storage\infrastructure\repository.py
import uuid
from typing import Optional, Sequence

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.storage.infrastructure.models import StorageObject

logger = structlog.get_logger(__name__)


class StorageObjectRepository:
    """
    Репозиторий для управления метаданными объектов S3.
    Реализует Append-Only подход для поддержки версионирования.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._logger = logger.bind(component="storage_object_repository")

    async def add(self, storage_object: StorageObject) -> None:
        """Добавление новой записи (версии) объекта."""
        self._session.add(storage_object)

    async def get_by_id(self, object_id: uuid.UUID) -> Optional[StorageObject]:
        """Получение метаданных по внутреннему UUID (используется другими модулями)."""
        return await self._session.get(StorageObject, object_id)

    async def get_active_by_key(
        self, bucket_name: str, object_key: str
    ) -> Optional[StorageObject]:
        """
        Получение актуальной версии файла по его S3 пути.
        """
        stmt = select(StorageObject).where(
            StorageObject.bucket_name == bucket_name,
            StorageObject.object_key == object_key,
            StorageObject.is_latest.is_(True),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_versions(
        self, bucket_name: str, object_key: str
    ) -> Sequence[StorageObject]:
        """
        Получение истории всех версий конкретного файла.
        Полезно для аудита и восстановления старых версий.
        """
        stmt = (
            select(StorageObject)
            .where(
                StorageObject.bucket_name == bucket_name,
                StorageObject.object_key == object_key,
            )
            .order_by(StorageObject.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

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
