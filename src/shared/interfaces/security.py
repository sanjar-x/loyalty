"""
Security service ports (Hexagonal Architecture).

Defines protocols for token management, password hashing, permission
resolution, and OIDC integration. Concrete implementations live in
``src.infrastructure.security``.

Typical usage:
    class LoginHandler:
        def __init__(
            self,
            tokens: ITokenProvider,
            hasher: IPasswordHasher,
        ) -> None:
            ...
"""

import uuid
from dataclasses import dataclass
from typing import Any, Protocol


class ITokenProvider(Protocol):
    """Contract for JWT generation and validation."""

    def create_access_token(
        self, payload_data: dict[str, Any], expires_minutes: int | None = None
    ) -> str:
        """Generate a signed JWT access token.

        Args:
            payload_data: Claims to embed in the token payload.
            expires_minutes: Override for the default expiration window.

        Returns:
            Encoded JWT string.
        """
        ...

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT access token.

        Args:
            token: Encoded JWT string.

        Returns:
            Decoded payload dictionary.

        Raises:
            UnauthorizedError: If the token is expired, malformed, or invalid.
        """
        ...

    def create_refresh_token(self) -> tuple[str, str]:
        """Generate an opaque refresh token.

        Returns:
            Tuple of (raw_token, sha256_hash). The raw token is sent
            to the client; the hash is stored server-side.
        """
        ...


class IPasswordHasher(Protocol):
    """Contract for password hashing and verification."""

    def hash(self, password: str) -> str:
        """Produce a one-way hash of the given plaintext password.

        Args:
            password: Plaintext password string.

        Returns:
            Algorithm-prefixed hash string.
        """
        ...

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a stored hash.

        Args:
            plain_password: Plaintext password to check.
            hashed_password: Stored hash to compare against.

        Returns:
            True if the password matches.
        """
        ...

    def needs_rehash(self, hashed_password: str) -> bool:
        """Check if the hash uses a legacy algorithm and needs re-hashing.

        Args:
            hashed_password: Stored hash to inspect.

        Returns:
            True if the hash should be upgraded on next login.
        """
        ...


class IPermissionResolver(Protocol):
    """Cache-aside permission resolver.

    Checks Redis SET first, falls back to a recursive CTE query,
    then caches the result. Used by the authorization middleware.
    """

    async def get_permissions(self, session_id: uuid.UUID) -> frozenset[str]:
        """Return all effective permission codenames for a session.

        Args:
            session_id: UUID of the active session.

        Returns:
            Frozen set of permission codename strings.
        """
        ...

    async def has_permission(self, session_id: uuid.UUID, codename: str) -> bool:
        """Check whether a session holds a specific permission.

        Args:
            session_id: UUID of the active session.
            codename: Permission codename to check (e.g. ``"catalog:manage"``).

        Returns:
            True if the session has the permission.
        """
        ...

    async def invalidate(self, session_id: uuid.UUID) -> None:
        """Delete cached permissions for a session.

        Called on role change or logout to force a fresh DB lookup.

        Args:
            session_id: UUID of the session whose cache should be cleared.
        """
        ...


@dataclass(frozen=True)
class OIDCUserInfo:
    """Normalized user info returned by an OIDC provider.

    Attributes:
        provider: OIDC provider identifier (e.g. ``"google"``, ``"github"``).
        sub: Provider-specific subject identifier.
        email: Email address if the provider returned one.
    """

    provider: str
    sub: str
    email: str | None = None


class IOIDCProvider(Protocol):
    """Abstract OIDC provider — extension point for future integrations."""

    async def validate_token(self, token: str) -> OIDCUserInfo:
        """Validate an OIDC token and return normalized user info.

        Args:
            token: Raw OIDC token string from the client.

        Returns:
            Normalized ``OIDCUserInfo`` with provider, sub, and email.

        Raises:
            UnauthorizedError: If the token is invalid or expired.
        """
        ...

    async def get_authorization_url(self, state: str) -> str:
        """Build the provider-specific OAuth2 authorization URL.

        Args:
            state: Opaque CSRF state parameter to round-trip.

        Returns:
            Full authorization URL for client redirect.
        """
        ...
