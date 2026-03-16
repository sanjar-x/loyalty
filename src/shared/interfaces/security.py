# src/shared/interfaces/security.py
import uuid
from dataclasses import dataclass
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

    def create_refresh_token(self) -> tuple[str, str]:
        """Generate opaque refresh token. Returns (raw_token, sha256_hash)."""
        ...


class IPasswordHasher(Protocol):
    """Контракт для работы с паролями."""

    def hash(self, password: str) -> str:
        """Сгенерировать хеш пароля."""
        ...

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Проверить пароль."""
        ...

    def needs_rehash(self, hashed_password: str) -> bool:
        """Check if hash uses legacy algorithm and needs re-hashing."""
        ...


class IPermissionResolver(Protocol):
    """
    Cache-Aside permission resolver.
    Redis SET → CTE fallback → cache result.
    """

    async def get_permissions(self, session_id: uuid.UUID) -> frozenset[str]:
        """Get all effective permission codenames for session."""
        ...

    async def has_permission(self, session_id: uuid.UUID, codename: str) -> bool:
        """Check if session has specific permission."""
        ...

    async def invalidate(self, session_id: uuid.UUID) -> None:
        """Delete cached permissions for session (on role change/logout)."""
        ...


@dataclass(frozen=True)
class OIDCUserInfo:
    """Normalized user info from OIDC provider."""

    provider: str
    sub: str
    email: str | None = None


class IOIDCProvider(Protocol):
    """Abstract OIDC provider. No implementations in v1 — extension point."""

    async def validate_token(self, token: str) -> OIDCUserInfo:
        """Validate OIDC token and return normalized user info."""
        ...

    async def get_authorization_url(self, state: str) -> str:
        """Get provider-specific authorization URL."""
        ...
