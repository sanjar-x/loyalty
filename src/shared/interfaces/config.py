# src/shared/interfaces/config.py
from typing import Protocol


class IStorageConfig(Protocol):
    """Контракт конфигурации для работы с объектным хранилищем (S3)."""

    S3_BUCKET_NAME: str
    S3_PUBLIC_BASE_URL: str
