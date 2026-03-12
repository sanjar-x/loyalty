# src/shared/interfaces/security.py
from typing import Any, Protocol


class ITokenProvider(Protocol):
    """Контракт для генерации и валидации security-токенов."""

    def create_access_token(
        self, payload_data: dict[str, Any], expires_minutes: int | None = None
    ) -> str:
        """Сгенерировать токен."""
        ...

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """Расшифровать токен и вернуть payload."""
        ...


class IPasswordHasher(Protocol):
    """Контракт для работы с паролями."""

    def hash(self, password: str) -> str:
        """Сгенерировать хеш пароля."""
        ...

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Проверить пароль."""
        ...
