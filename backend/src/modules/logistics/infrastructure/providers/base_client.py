"""
Base HTTP client for logistics provider adapters.

Provides retry with exponential backoff + jitter, configurable timeouts,
automatic auth header injection, structured logging, and error mapping.
Each concrete provider adapter composes this client rather than
implementing raw HTTP calls.
"""

import asyncio
import logging
import random
from typing import Any

import attrs
import httpx

from src.modules.logistics.infrastructure.providers.base_auth import BaseAuthManager
from src.modules.logistics.infrastructure.providers.errors import (
    ProviderAuthError,
    ProviderHTTPError,
    ProviderTimeoutError,
)

logger = logging.getLogger(__name__)

# HTTP status codes that trigger automatic retry
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

# Maximum number of characters of an error response body kept in
# ``ProviderHTTPError.response_body``. CDEK validation errors can carry
# 50+ entries — 8 KiB is enough to retain full debugging context without
# blowing up logs.
_RESPONSE_BODY_LOG_LIMIT = 8000


@attrs.define(frozen=True)
class ProviderClientConfig:
    """HTTP client configuration for a logistics provider.

    Infrastructure concern — lives alongside the client that uses it.
    """

    base_url: str
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_base_delay: float = 1.0


class BaseProviderClient:
    """Shared HTTP client infrastructure for logistics provider adapters.

    Usage::

        client = BaseProviderClient(auth_manager, config)
        async with client:
            response = await client.request("POST", "/v2/calculator/tariff", json={...})

    Features:
        - Auth header injection via ``BaseAuthManager``
        - Retry with exponential backoff + jitter on 429/5xx
        - Configurable timeout per request
        - Structured request/response logging
        - Unified error mapping to ``ProviderHTTPError`` / ``ProviderTimeoutError``
    """

    def __init__(
        self,
        auth_manager: BaseAuthManager,
        config: ProviderClientConfig,
    ) -> None:
        self._auth: BaseAuthManager = auth_manager
        self._config: ProviderClientConfig = config
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> BaseProviderClient:
        self._client = httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=httpx.Timeout(self._config.timeout_seconds),
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "BaseProviderClient must be used as an async context manager"
            )
        return self._client

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        content: bytes | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with auth, retry, and logging.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE).
            path: URL path relative to the provider base URL.
            json: JSON request body.
            params: URL query parameters.
            headers: Additional headers (merged with auth headers).
            data: Form-encoded request body.
            content: Raw bytes request body.

        Returns:
            The ``httpx.Response`` from the provider.

        Raises:
            ProviderHTTPError: Non-retryable HTTP error (4xx except 429).
            ProviderTimeoutError: All retries exhausted due to timeouts.
            ProviderAuthError: Authentication failure.
        """
        await self._auth.refresh_if_needed()
        auth_headers = await self._auth.get_auth_headers()

        merged_headers = {**auth_headers}
        if headers:
            merged_headers.update(headers)

        last_exception: Exception | None = None

        for attempt in range(1, self._config.max_retries + 1):
            try:
                logger.debug(
                    "Provider request attempt %d/%d: %s %s",
                    attempt,
                    self._config.max_retries,
                    method,
                    path,
                )

                response = await self.client.request(
                    method=method,
                    url=path,
                    json=json,
                    params=params,
                    headers=merged_headers,
                    data=data,
                    content=content,
                )

                if response.status_code < 400:
                    return response

                if response.status_code == 401:
                    # Force token refresh and retry once
                    if attempt == 1:
                        await self._auth.refresh_if_needed()
                        auth_headers = await self._auth.get_auth_headers()
                        merged_headers.update(auth_headers)
                        continue
                    raise ProviderAuthError(
                        f"Authentication failed after refresh: HTTP {response.status_code}"
                    )

                if response.status_code in _RETRYABLE_STATUS_CODES:
                    last_exception = ProviderHTTPError(
                        status_code=response.status_code,
                        message=f"Retryable error on attempt {attempt}",
                        response_body=response.text[:_RESPONSE_BODY_LOG_LIMIT],
                    )
                    if attempt < self._config.max_retries:
                        await self._backoff(attempt)
                        continue
                    raise last_exception

                # Non-retryable client error (400, 403, 404, 409, 422, etc.)
                raise ProviderHTTPError(
                    status_code=response.status_code,
                    message=response.reason_phrase or "",
                    response_body=response.text[:_RESPONSE_BODY_LOG_LIMIT],
                )

            except httpx.TimeoutException:
                last_exception = ProviderTimeoutError(
                    f"Timeout on attempt {attempt}/{self._config.max_retries}"
                )
                if attempt < self._config.max_retries:
                    await self._backoff(attempt)
                    continue

            except (ProviderHTTPError, ProviderAuthError, ProviderTimeoutError):
                raise

            except httpx.HTTPError as exc:
                last_exception = ProviderHTTPError(
                    status_code=0,
                    message=f"Connection error: {exc}",
                )
                if attempt < self._config.max_retries:
                    await self._backoff(attempt)
                    continue

        raise last_exception or ProviderTimeoutError("All retries exhausted")

    async def _backoff(self, attempt: int) -> None:
        """Exponential backoff with jitter."""
        base_delay = self._config.retry_base_delay
        delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, base_delay)
        logger.debug("Backing off for %.2f seconds before retry", delay)
        await asyncio.sleep(delay)
