# src/shared/interfaces/cache.py
from typing import Protocol


class ICacheService(Protocol):
    """Контракт сервиса кэширования."""

    async def set(self, key: str, value: str, ttl: int = 0) -> None:
        """Сохранить значение. ttl — время жизни в секундах (0 = без истечения)."""
        ...

    async def get(self, key: str) -> str | None:
        """Получить значение по ключу."""
        ...

    async def delete(self, key: str) -> None:
        """Удалить значение по ключу."""
        ...
