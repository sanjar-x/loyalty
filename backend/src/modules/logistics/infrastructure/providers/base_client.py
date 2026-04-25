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

# HTTP status codes safe to retry for *any* method (idempotent or not):
# 429 is rate-limit back-off — replaying does not produce a duplicate
# resource.
_ALWAYS_RETRYABLE_STATUS_CODES = frozenset({429})

# Status codes safe to retry only when the HTTP method is itself
# idempotent (RFC 7231 §4.2.2). For non-idempotent calls — POST without
# an Idempotency-Key — replaying a 5xx / timeout risks duplicate orders /
# bookings on the carrier side. CDEK dedupes online-store orders by
# ``number`` server-side, but Yandex ``offers/create``,
# ``offers/confirm``, ``request/create`` carry no client key.
_IDEMPOTENT_RETRY_STATUS_CODES = frozenset({500, 502, 503, 504})

# Methods whose semantics are idempotent per RFC 7231 / RFC 5789.
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "PUT", "DELETE", "OPTIONS"})

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
        self._client_lock: asyncio.Lock = asyncio.Lock()

    async def __aenter__(self) -> BaseProviderClient:
        # Kept for backwards-compatible test fixtures. Production code
        # opens the client lazily on the first request and closes it
        # via ``close()`` at app shutdown.
        await self._ensure_client()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying httpx client.

        Called at app shutdown via the bootstrap lifespan hook. Safe to
        call multiple times — subsequent invocations no-op.
        """
        async with self._client_lock:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Open the underlying httpx client on first use.

        Subsequent calls reuse the same instance. Concurrent first
        requests race through ``_client_lock`` so only one client is
        ever created — the previous design opened-then-closed a fresh
        client per request, which under load closed in-flight requests
        from sibling coroutines (review item C1).
        """
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(
                        base_url=self._config.base_url,
                        timeout=httpx.Timeout(self._config.timeout_seconds),
                    )
        return self._client

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "BaseProviderClient.client accessed before _ensure_client(); "
                "call request() instead of touching .client directly."
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
        retry_idempotent: bool | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with auth, retry, and logging.

        Retry policy is *method-aware*:

        - Every method retries on HTTP 429 (rate-limit) — safe to replay.
        - Only idempotent methods (GET / HEAD / PUT / DELETE / OPTIONS)
          retry on 5xx and on transport errors (timeouts, connection
          drops). Non-idempotent POST / PATCH must opt in via
          ``retry_idempotent=True`` after the caller has guaranteed
          server-side deduplication (e.g. an Idempotency-Key header).

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE).
            path: URL path relative to the provider base URL.
            json: JSON request body.
            params: URL query parameters.
            headers: Additional headers (merged with auth headers).
            data: Form-encoded request body.
            content: Raw bytes request body.
            retry_idempotent: Override the auto-detected idempotency
                hint. ``True`` forces 5xx / timeout retries on
                non-idempotent methods (caller must supply an
                idempotency key); ``False`` disables 5xx retries even
                for naturally idempotent methods. Defaults to
                ``method.upper() in _IDEMPOTENT_METHODS``.

        Returns:
            The ``httpx.Response`` from the provider.

        Raises:
            ProviderHTTPError: Non-retryable HTTP error (4xx except 429).
            ProviderTimeoutError: All retries exhausted due to timeouts.
            ProviderAuthError: Authentication failure.
        """
        retry_5xx = (
            retry_idempotent
            if retry_idempotent is not None
            else method.upper() in _IDEMPOTENT_METHODS
        )

        client = await self._ensure_client()

        await self._auth.refresh_if_needed()
        auth_headers = await self._auth.get_auth_headers()

        merged_headers = {**auth_headers}
        if headers:
            merged_headers.update(headers)

        last_exception: Exception | None = None
        auth_refreshed = False

        for attempt in range(1, self._config.max_retries + 1):
            try:
                logger.debug(
                    "Provider request attempt %d/%d: %s %s",
                    attempt,
                    self._config.max_retries,
                    method,
                    path,
                )

                response = await client.request(
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
                    # Force a *real* token refresh once per request
                    # lifetime — ``refresh_if_needed`` is clock-driven
                    # and no-ops when our local cache thinks the
                    # token is fresh, but the carrier may have
                    # invalidated it server-side. ``force_refresh``
                    # discards the cached token and re-fetches.
                    # Tracked via a local flag rather than
                    # ``attempt == 1`` so a transient 5xx burning the
                    # first attempt does not block a legitimate
                    # refresh on the next one.
                    if not auth_refreshed:
                        auth_refreshed = True
                        await self._auth.force_refresh()
                        auth_headers = await self._auth.get_auth_headers()
                        merged_headers.update(auth_headers)
                        # 401 is auth, not a 5xx — don't burn a retry
                        # slot before the refreshed token gets a turn.
                        if attempt == self._config.max_retries:
                            raise ProviderAuthError(
                                "Authentication failed: token refreshed "
                                "but no retry budget remains"
                            )
                        continue
                    raise ProviderAuthError(
                        f"Authentication failed after refresh: HTTP {response.status_code}"
                    )

                is_rate_limited = response.status_code in _ALWAYS_RETRYABLE_STATUS_CODES
                is_5xx_retryable = (
                    retry_5xx and response.status_code in _IDEMPOTENT_RETRY_STATUS_CODES
                )
                if is_rate_limited or is_5xx_retryable:
                    last_exception = ProviderHTTPError(
                        status_code=response.status_code,
                        message=f"Retryable error on attempt {attempt}",
                        response_body=response.text[:_RESPONSE_BODY_LOG_LIMIT],
                    )
                    if attempt < self._config.max_retries:
                        await self._backoff(attempt)
                        continue
                    raise last_exception

                # 5xx on a non-idempotent call — surface immediately so
                # the caller can decide whether to retry with a new
                # idempotency key.
                if response.status_code in _IDEMPOTENT_RETRY_STATUS_CODES:
                    raise ProviderHTTPError(
                        status_code=response.status_code,
                        message=(
                            f"{method} returned {response.status_code}; "
                            "not retrying — caller must supply an "
                            "idempotency key to enable retries."
                        ),
                        response_body=response.text[:_RESPONSE_BODY_LOG_LIMIT],
                    )

                # Non-retryable client error (400, 403, 404, 409, 422, etc.)
                raise ProviderHTTPError(
                    status_code=response.status_code,
                    message=response.reason_phrase or "",
                    response_body=response.text[:_RESPONSE_BODY_LOG_LIMIT],
                )

            except httpx.TimeoutException as timeout_exc:
                # Transport-level failure: we cannot tell whether the
                # server processed the request, so retrying is only
                # safe for idempotent methods.
                last_exception = ProviderTimeoutError(
                    f"Timeout on attempt {attempt}/{self._config.max_retries}"
                )
                if retry_5xx and attempt < self._config.max_retries:
                    await self._backoff(attempt)
                    continue
                raise last_exception from timeout_exc

            except (
                ProviderHTTPError,
                ProviderAuthError,
                ProviderTimeoutError,
            ) as _exc:
                raise

            except httpx.HTTPError as exc:
                last_exception = ProviderHTTPError(
                    status_code=0,
                    message=f"Connection error: {exc}",
                )
                if retry_5xx and attempt < self._config.max_retries:
                    await self._backoff(attempt)
                    continue
                raise last_exception from exc

        raise last_exception or ProviderTimeoutError("All retries exhausted")

    async def _backoff(self, attempt: int) -> None:
        """Exponential backoff with jitter."""
        base_delay = self._config.retry_base_delay
        delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, base_delay)
        logger.debug("Backing off for %.2f seconds before retry", delay)
        await asyncio.sleep(delay)
