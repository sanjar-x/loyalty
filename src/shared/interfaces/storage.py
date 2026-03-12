# src/shared/interfaces/storage.py
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Protocol


@dataclass(frozen=True)
class PresignedUploadData:
    url_data: dict | str
    object_key: str


class IStorageFacade(Protocol):
    """
    Публичный API модуля Storage (Facade Pattern).
    Скрывает под собой работу с IBlobStorage (S3) и БД (IStorageRepository).
    """

    async def request_upload(
        self, module: str, entity_id: str | uuid.UUID, filename: str
    ) -> PresignedUploadData:
        """
        Запрашивает временную ссылку для прямой загрузки файла (Direct-to-S3).
        Вся логика путей (prefixes) инкапсулирована внутри.
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
        """
        Запрашивает временную ссылку для прямой PUT загрузки файла в S3 (Direct-to-S3).
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
        """
        Регистрирует метаданные обработанного файла в БД и возвращает ID файла.
        """
        ...

    async def verify_module_upload(
        self, module: str, entity_id: str | uuid.UUID
    ) -> Dict[str, Any]:
        """
        Проверяет, был ли загружен файл для конкретной сущности.
        Возвращает метаданные файла, где 'object_key' — точный путь найденного файла.
        """
        ...
