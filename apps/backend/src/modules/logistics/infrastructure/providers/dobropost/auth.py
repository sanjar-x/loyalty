"""DobroPost auth manager — email/password → JWT (12h fixed TTL).

DobroPost issues a JWT through a single endpoint
``POST /api/shipment/sign-in {email, password}`` and returns
``{"token": "..."}`` with **no ``expires_in``**. The TTL is fixed at 12
hours per ``reference.md`` §1. We track local issue time and refresh 5
minutes before expiry.

A 401 from any subsequent request triggers ``force_refresh`` (handled
by ``BaseProviderClient`` automatically) — discards the cached token
and re-fetches.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx

from src.modules.logistics.infrastructure.providers.base_auth import BaseAuthManager
from src.modules.logistics.infrastructure.providers.dobropost.constants import (
    DOBROPOST_SIGN_IN_PATH,
    DOBROPOST_TOKEN_REFRESH_BUFFER_SECONDS,
    DOBROPOST_TOKEN_TTL_SECONDS,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderAuthError


class DobroPostAuthManager(BaseAuthManager):
    """Email/password → JWT auth with locally-tracked 12h TTL.

    Caches the token in-memory (per APP-scoped factory instance) and
    serialises concurrent refreshes through ``_lock``.
    """

    def __init__(
        self,
        base_url: str,
        email: str,
        password: str,
        *,
        sign_in_timeout_seconds: float = 10.0,
    ) -> None:
        self._token_url = f"{base_url}{DOBROPOST_SIGN_IN_PATH}"
        self._email = email
        self._password = password
        self._sign_in_timeout = sign_in_timeout_seconds
        self._buffer = timedelta(seconds=DOBROPOST_TOKEN_REFRESH_BUFFER_SECONDS)
        self._token: str | None = None
        self._expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def get_auth_headers(self) -> dict[str, str]:
        await self.refresh_if_needed()
        if self._token is None:
            raise ProviderAuthError("Failed to acquire DobroPost token")
        return {"Authorization": f"Bearer {self._token}"}

    async def refresh_if_needed(self) -> None:
        if self._token_is_fresh():
            return
        await self._fetch_token_locked()

    async def force_refresh(self) -> None:
        async with self._lock:
            self._token = None
            self._expires_at = None
        await self._fetch_token_locked()

    def _token_is_fresh(self) -> bool:
        if self._token is None or self._expires_at is None:
            return False
        return datetime.now(UTC) < (self._expires_at - self._buffer)

    async def _fetch_token_locked(self) -> None:
        async with self._lock:
            if self._token_is_fresh():
                return  # another waiter already refreshed
            async with httpx.AsyncClient(timeout=self._sign_in_timeout) as client:
                response = await client.post(
                    self._token_url,
                    json={"email": self._email, "password": self._password},
                )
                if response.status_code != 200:
                    raise ProviderAuthError(
                        "DobroPost sign-in failed: "
                        f"HTTP {response.status_code} {response.text[:200]}"
                    )
                data = response.json()
                token = data.get("token")
                if not token or not isinstance(token, str):
                    raise ProviderAuthError(
                        "DobroPost sign-in response missing 'token' field"
                    )
                self._token = token
                self._expires_at = datetime.now(UTC) + timedelta(
                    seconds=DOBROPOST_TOKEN_TTL_SECONDS
                )
