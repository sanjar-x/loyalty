"""Real DobroPost HTTP client.

Implements the JWT auth + ``POST /api/shipment`` contract from
research §10. Used by the ``DobroPostGatewayReal`` adapter when the
``DOBROPOST_USE_STUB=false`` flag is on.

Token lifecycle:
* Sign-in returns a JWT with TTL 12h.
* The client caches the token + expiry in a process-local dict and
  refreshes ahead of expiry via ``DOBROPOST_TOKEN_REFRESH_BEFORE_SECONDS``.
* On 401 from any protected endpoint, the client force-refreshes once
  and retries the original request.

Resiliency:
* Connection / read timeouts come from ``DOBROPOST_TIMEOUT_SECONDS``.
* Transient failures (network errors, HTTP 5xx, 429) are retried with
  exponential backoff up to ``DOBROPOST_RETRY_MAX_ATTEMPTS``.
* A simple in-memory circuit breaker trips after
  ``DOBROPOST_CIRCUIT_FAILURE_THRESHOLD`` consecutive failures; while
  open it short-circuits with ``CrossBorderProviderError`` and lets the
  caller fail fast. Half-opens after
  ``DOBROPOST_CIRCUIT_RESET_TIMEOUT_SECONDS``.
"""

from __future__ import annotations

import asyncio
import random
import time
from datetime import date
from typing import Any

import httpx
import structlog

from src.bootstrap.config import settings
from src.modules.order.domain.exceptions import CrossBorderProviderError

logger = structlog.get_logger(__name__)

_AUTH_TTL_SECONDS = 12 * 3600
_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class _CircuitOpenError(Exception):
    """Raised when the circuit-breaker is open."""


class _CircuitBreaker:
    """Closed → Open → Half-Open → Closed simple state machine.

    Counts only consecutive failures; one success in half-open closes
    the circuit. Thread-safe under asyncio (single-loop).
    """

    def __init__(self, *, threshold: int, reset_timeout: float) -> None:
        self._threshold = threshold
        self._reset_timeout = reset_timeout
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if time.monotonic() - self._opened_at < self._reset_timeout:
            return "open"
        return "half_open"

    def before_call(self) -> None:
        if self.state == "open":
            raise _CircuitOpenError("DobroPost circuit-breaker is open — failing fast")

    def on_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def on_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold and self._opened_at is None:
            self._opened_at = time.monotonic()
            logger.warning(
                "dobropost.circuit.open",
                failures=self._failures,
                reset_in_seconds=self._reset_timeout,
            )


class DobroPostHttpClient:
    """Thin async client around DobroPost ``api.dobropost.com``.

    The client is process-singleton (APP scope in Dishka) — the auth
    token cache + circuit-breaker are in-memory.
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.DOBROPOST_BASE_URL,
            timeout=httpx.Timeout(
                settings.DOBROPOST_TIMEOUT_SECONDS,
                connect=min(5.0, settings.DOBROPOST_TIMEOUT_SECONDS),
            ),
        )
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._token_lock = asyncio.Lock()
        self._breaker = _CircuitBreaker(
            threshold=settings.DOBROPOST_CIRCUIT_FAILURE_THRESHOLD,
            reset_timeout=settings.DOBROPOST_CIRCUIT_RESET_TIMEOUT_SECONDS,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def _sign_in(self) -> None:
        email = settings.DOBROPOST_EMAIL.get_secret_value()
        password = settings.DOBROPOST_PASSWORD.get_secret_value()
        if not email or not password:
            raise RuntimeError(
                "DobroPost credentials are not configured "
                "(DOBROPOST_EMAIL / DOBROPOST_PASSWORD)"
            )
        resp = await self._client.post(
            "/api/shipment/sign-in",
            json={"email": email, "password": password},
        )
        if resp.status_code != 200:
            logger.error(
                "dobropost.sign_in_failed",
                status=resp.status_code,
                body=resp.text[:500],
            )
            raise RuntimeError(f"DobroPost sign-in failed: HTTP {resp.status_code}")
        data = resp.json()
        token = data.get("token")
        if not token:
            raise RuntimeError("DobroPost sign-in response missing 'token'")
        self._token = token
        self._token_expires_at = time.time() + _AUTH_TTL_SECONDS
        logger.info("dobropost.sign_in_ok")

    async def _ensure_token(self, *, force_refresh: bool = False) -> str:
        margin = settings.DOBROPOST_TOKEN_REFRESH_BEFORE_SECONDS
        async with self._token_lock:
            if (
                force_refresh
                or self._token is None
                or time.time() + margin >= self._token_expires_at
            ):
                await self._sign_in()
            assert self._token is not None
            return self._token

    # ------------------------------------------------------------------
    # Shipment endpoints
    # ------------------------------------------------------------------

    async def create_shipment(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._authed_request("POST", "/api/shipment", json=payload)

    async def update_shipment(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._authed_request("PUT", "/api/shipment", json=payload)

    async def list_shipments(
        self,
        *,
        page: int = 1,
        offset: int = 50,
        status_id: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "offset": offset}
        if status_id is not None:
            params["statusId"] = status_id
        return await self._authed_request("GET", "/api/shipment", params=params)

    async def delete_shipment(self, shipment_id: int) -> None:
        await self._authed_request("DELETE", f"/api/shipment/{shipment_id}")

    # ------------------------------------------------------------------
    # Internals — retry + circuit breaker
    # ------------------------------------------------------------------

    async def _authed_request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        try:
            self._breaker.before_call()
        except _CircuitOpenError as exc:
            raise CrossBorderProviderError(
                provider="dobropost", reason="circuit_open"
            ) from exc

        attempts = max(1, settings.DOBROPOST_RETRY_MAX_ATTEMPTS)
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                resp = await self._do_authed_request(
                    method, path, json=json, params=params
                )
            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.RemoteProtocolError,
            ) as exc:
                last_exc = exc
                logger.warning(
                    "dobropost.transport_error",
                    method=method,
                    path=path,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt < attempts:
                    await self._sleep_backoff(attempt)
                    continue
                self._breaker.on_failure()
                raise CrossBorderProviderError(
                    provider="dobropost",
                    reason=f"transport_error: {exc.__class__.__name__}",
                ) from exc

            if resp.status_code in _RETRYABLE_STATUS and attempt < attempts:
                logger.warning(
                    "dobropost.retryable_status",
                    method=method,
                    path=path,
                    attempt=attempt,
                    status=resp.status_code,
                )
                await self._sleep_backoff(
                    attempt, retry_after=resp.headers.get("Retry-After")
                )
                continue

            if not 200 <= resp.status_code < 300:
                logger.error(
                    "dobropost.api_error",
                    method=method,
                    path=path,
                    status=resp.status_code,
                    body=resp.text[:500],
                )
                self._breaker.on_failure()
                raise CrossBorderProviderError(
                    provider="dobropost",
                    reason=f"HTTP {resp.status_code}",
                )

            self._breaker.on_success()
            if resp.headers.get("content-type", "").startswith("application/json"):
                return resp.json()
            return {}

        # Unreachable; defensive.
        if last_exc is not None:  # pragma: no cover
            raise CrossBorderProviderError(
                provider="dobropost", reason="exhausted_retries"
            ) from last_exc
        raise CrossBorderProviderError(  # pragma: no cover
            provider="dobropost", reason="exhausted_retries"
        )

    async def _do_authed_request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None,
        params: dict | None,
    ) -> httpx.Response:
        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}"}
        resp = await self._client.request(
            method, path, headers=headers, json=json, params=params
        )
        if resp.status_code == 401:
            token = await self._ensure_token(force_refresh=True)
            headers = {"Authorization": f"Bearer {token}"}
            resp = await self._client.request(
                method, path, headers=headers, json=json, params=params
            )
        return resp

    async def _sleep_backoff(
        self, attempt: int, *, retry_after: str | None = None
    ) -> None:
        if retry_after:
            try:
                await asyncio.sleep(float(retry_after))
                return
            except ValueError:
                pass
        base = settings.DOBROPOST_RETRY_BACKOFF_BASE_SECONDS
        cap = settings.DOBROPOST_RETRY_BACKOFF_MAX_SECONDS
        delay = min(cap, base * (2 ** (attempt - 1)))
        # Decorrelated jitter: random in [base, delay*3]
        jitter = random.uniform(base, max(base * 1.01, delay * 3))
        await asyncio.sleep(min(cap, jitter))


def build_shipment_payload(
    *,
    full_name_lat: str,
    phone: str,
    email: str,
    passport_serial: str,
    passport_number: str,
    passport_issue_date: date,
    birth_date: date,
    inn: str,
    incoming_declaration: str,
    items: list[dict],
    pickup_address: str,
    pickup_postcode: str,
    tariff_id: int,
) -> dict[str, Any]:
    """Build the DobroPost ``POST /api/shipment`` body.

    Keys follow DobroPost spec (research §10.3 — note the
    ``vatIdentificationNumber`` capitalization quirk on request).
    """
    return {
        "consignee": {
            "fullName": full_name_lat,
            "phone": phone,
            "email": email,
        },
        "consigneePassportSerial": passport_serial,
        "consigneePassportNumber": passport_number,
        "passportIssueDate": passport_issue_date.isoformat(),
        "consigneeBirthDate": birth_date.isoformat(),
        "vatIdentificationNumber": inn,
        "incomingDeclaration": incoming_declaration,
        "items": items,
        "pickupAddress": pickup_address,
        "pickupPostcode": pickup_postcode,
        "dpTariffId": tariff_id,
    }


def build_update_shipment_payload(
    *,
    shipment_id: int,
    full_name_lat: str,
    phone: str,
    email: str,
    passport_serial: str,
    passport_number: str,
    passport_issue_date: date,
    birth_date: date,
    inn: str,
) -> dict[str, Any]:
    """Build the DobroPost ``PUT /api/shipment`` body for recipient updates.

    Used after RefreshRecipientSnapshot — pushes the corrected passport
    + customs details back so DobroPost re-validates.
    """
    return {
        "id": shipment_id,
        "consignee": {
            "fullName": full_name_lat,
            "phone": phone,
            "email": email,
        },
        "consigneePassportSerial": passport_serial,
        "consigneePassportNumber": passport_number,
        "passportIssueDate": passport_issue_date.isoformat(),
        "consigneeBirthDate": birth_date.isoformat(),
        "vatIdentificationNumber": inn,
    }
