"""JWT token provider implementation for access and refresh tokens.

Handles creation and decoding of JWT access tokens, as well as
generation of opaque refresh tokens with SHA-256 hashing for
secure database storage.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from src.bootstrap.config import settings
from src.shared.exceptions import UnauthorizedError
from src.shared.interfaces.security import ITokenProvider


class JwtTokenProvider(ITokenProvider):
    """Token provider that issues and verifies JWT access tokens."""

    def create_access_token(
        self, payload_data: dict[str, Any], expires_minutes: int | None = None
    ) -> str:
        """Create a signed JWT access token.

        Args:
            payload_data: Claims to include in the token payload.
            expires_minutes: Custom expiration in minutes. Falls back to
                the configured ``ACCESS_TOKEN_EXPIRE_MINUTES`` if not provided.

        Returns:
            The encoded JWT string.
        """
        to_encode = payload_data.copy()

        now = datetime.now(tz=UTC)
        if expires_minutes is not None:
            expire = now + timedelta(minutes=expires_minutes)
        else:
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update(
            {
                "exp": expire,
                "iat": now,
                "jti": str(uuid.uuid4()),
            }
        )

        encoded_jwt: str = jwt.encode(
            to_encode,
            key=settings.SECRET_KEY.get_secret_value(),
            algorithm=settings.ALGORITHM,
        )
        return encoded_jwt

    def create_refresh_token(self) -> tuple[str, str]:
        """Generate an opaque refresh token.

        Returns:
            A tuple of ``(raw_token, sha256_hash)``. The raw token is sent
            to the client; the hash is stored in the database.
        """
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        return raw_token, token_hash

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT access token.

        Args:
            token: The encoded JWT string.

        Returns:
            The decoded token payload as a dictionary.

        Raises:
            UnauthorizedError: If the token has expired or is invalid.
        """
        try:
            decoded_token: dict[str, Any] = jwt.decode(
                jwt=token,
                key=settings.SECRET_KEY.get_secret_value(),
                algorithms=[settings.ALGORITHM],
            )
            return decoded_token

        except ExpiredSignatureError as e:
            raise UnauthorizedError(
                message="Token has expired. Please re-authenticate.",
                error_code="TOKEN_EXPIRED",
            ) from e
        except InvalidTokenError as e:
            raise UnauthorizedError(
                message="Invalid access token.", error_code="INVALID_TOKEN"
            ) from e
