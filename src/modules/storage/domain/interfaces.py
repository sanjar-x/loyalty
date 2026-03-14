# src/modules/storage/domain/interfaces.py

import uuid
from typing import Optional, Protocol, Sequence

from src.modules.storage.infrastructure.models import StorageObject


class IStorageRepository(Protocol):
    """Доменный контракт для работы с хранилищем метаданных файлов."""

    async def add(self, storage_object: StorageObject) -> None: ...
    async def get_by_key(self, key: uuid.UUID) -> Optional[StorageObject]: ...
    async def get_active_by_key(
        self, bucket_name: str, object_key: str
    ) -> Optional[StorageObject]: ...
    async def get_all_versions(
        self, bucket_name: str, object_key: str
    ) -> Sequence[StorageObject]: ...
    async def deactivate_previous_versions(
        self, bucket_name: str, object_key: str
    ) -> None: ...
    async def mark_as_deleted(self, bucket_name: str, object_key: str) -> None: ...
