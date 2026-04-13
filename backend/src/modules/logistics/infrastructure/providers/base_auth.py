"""
Base authentication managers for logistics provider HTTP clients.

Each provider uses a different auth scheme — the ``BaseAuthManager``
abstract class defines the contract, and concrete implementations
handle token acquisition, caching, and refresh.
"""

import asyncio
import base64
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

import httpx

from src.modules.logistics.infrastructure.providers.errors import ProviderAuthError


class BaseAuthManager(ABC):
    """Abstract base for provider authentication."""

    @abstractmethod
    async def get_auth_headers(self) -> dict[str, str]:
        """Return HTTP headers required for authenticated requests."""
        ...

    @abstractmethod
    async def refresh_if_needed(self) -> None:
        """Refresh credentials if expired or about to expire."""
        ...


class BearerTokenAuthManager(BaseAuthManager):
    """Static Bearer token authentication (e.g. Yandex Delivery).

    The token does not expire and is passed as-is.
    """

    def __init__(self, token: str) -> None:
        self._token = token

    async def get_auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    async def refresh_if_needed(self) -> None:
        pass  # static token, no refresh


class OAuth2ClientCredentialsAuthManager(BaseAuthManager):
    """OAuth2 client_credentials grant (e.g. CDEK).

    Acquires a JWT access token from the provider's token endpoint,
    caches it, and refreshes before expiry.
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        *,
        token_expiry_buffer_seconds: int = 60,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._buffer = timedelta(seconds=token_expiry_buffer_seconds)
        self._access_token: str | None = None
        self._expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def get_auth_headers(self) -> dict[str, str]:
        await self.refresh_if_needed()
        if self._access_token is None:
            raise ProviderAuthError("Failed to acquire OAuth2 token")
        return {"Authorization": f"Bearer {self._access_token}"}

    async def refresh_if_needed(self) -> None:
        now = datetime.now(UTC)
        if (
            self._access_token
            and self._expires_at
            and now < (self._expires_at - self._buffer)
        ):
            return  # token still valid

        async with self._lock:
            # Double-check after acquiring the lock
            now = datetime.now(UTC)
            if (
                self._access_token
                and self._expires_at
                and now < (self._expires_at - self._buffer)
            ):
                return

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self._token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                    },
                )
                if response.status_code != 200:
                    raise ProviderAuthError(
                        f"OAuth2 token request failed: HTTP {response.status_code}"
                    )
                data = response.json()
                self._access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self._expires_at = now + timedelta(seconds=expires_in)


class DualHeaderAuthManager(BaseAuthManager):
    """Dual-header authentication (e.g. Russian Post).

    Sends two headers:
    - ``Authorization: AccessToken <token>``
    - ``X-User-Authorization: Basic <base64(login:password)>``
    """

    def __init__(
        self,
        access_token: str,
        login: str,
        password: str,
    ) -> None:
        self._access_token = access_token
        self._basic_auth = base64.b64encode(f"{login}:{password}".encode()).decode()

    async def get_auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"AccessToken {self._access_token}",
            "X-User-Authorization": f"Basic {self._basic_auth}",
        }

    async def refresh_if_needed(self) -> None:
        pass  # static credentials
