"""Telegram Bot API ``sendMessage`` wrapper for ops alerts (HARD-2).

The alerter is intentionally minimal: one method, no per-call
configuration, never raises into the caller. Failure semantics:

* If ``BOT_TOKEN`` or ``TG_ALERTS_CHANNEL`` is unset, ``send`` is a
  no-op and logs a structured warning. The two scheduled monitors
  (and any future caller) keep running without modification.
* On HTTP 429 ``Too Many Requests`` the response carries a
  ``parameters.retry_after`` field per the Bot API spec; we honour
  it once and retry, then give up. Aggressive retry storms would
  defeat the purpose of an alert system — better to drop a tick than
  amplify the outage.
* On any other transport / HTTP error we log the exception and return
  False. Alert delivery failures must never take the calling
  scheduler / handler down.
"""

from __future__ import annotations

import asyncio

import httpx
import structlog

from src.bootstrap.config import settings

logger = structlog.get_logger(__name__)

_TELEGRAM_API_BASE = "https://api.telegram.org"
_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
_RETRY_AFTER_FALLBACK_SECONDS = 1.0


class TelegramAlerter:
    """Thin async client for ``sendMessage``.

    A single instance can be reused across many ``send`` calls.
    Network errors and Telegram API errors are logged; never raised.
    """

    def __init__(
        self,
        *,
        bot_token: str | None = None,
        chat_id: str | None = None,
        timeout: httpx.Timeout = _DEFAULT_TIMEOUT,
    ) -> None:
        self._bot_token = bot_token or settings.BOT_TOKEN.get_secret_value()
        self._chat_id = chat_id if chat_id is not None else settings.TG_ALERTS_CHANNEL
        self._timeout = timeout
        self._log = logger.bind(component="TelegramAlerter")

    async def send(self, text: str, *, disable_notification: bool = False) -> bool:
        """Send a plain-text message to the configured channel.

        Args:
            text: The pre-formatted alert body. Plain text only — see
                :mod:`alert_levels` for why MarkdownV2 is intentionally
                avoided.
            disable_notification: If True, the message lands silently
                (useful for INFO-level pings during a 24h warm period).

        Returns:
            ``True`` on confirmed delivery, ``False`` on any failure
            (including the no-op case when env vars are unset).
        """
        if not self._bot_token or not self._chat_id:
            self._log.warning(
                "alerter.disabled",
                reason="missing_bot_token_or_channel",
                has_token=bool(self._bot_token),
                has_channel=bool(self._chat_id),
            )
            return False

        url = f"{_TELEGRAM_API_BASE}/bot{self._bot_token}/sendMessage"
        payload: dict[str, object] = {
            "chat_id": self._chat_id,
            "text": text,
            "disable_notification": disable_notification,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._post_with_retry(client, url, payload)

    async def _post_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        payload: dict[str, object],
    ) -> bool:
        for attempt in (0, 1):  # one retry on 429
            try:
                response = await client.post(url, json=payload)
            except httpx.HTTPError as exc:
                self._log.error(
                    "alerter.transport_error",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    attempt=attempt,
                )
                return False

            if response.status_code == 200:
                return True

            if response.status_code == 429 and attempt == 0:
                retry_after = self._extract_retry_after(response)
                self._log.warning(
                    "alerter.rate_limited",
                    retry_after_seconds=retry_after,
                )
                await asyncio.sleep(retry_after)
                continue

            self._log.error(
                "alerter.http_error",
                status=response.status_code,
                body=response.text[:200],
                attempt=attempt,
            )
            return False

        return False

    @staticmethod
    def _extract_retry_after(response: httpx.Response) -> float:
        """Parse Telegram's ``retry_after`` from a 429 response body.

        Falls back to a 1-second sleep if the field is absent or
        malformed — Telegram's contract guarantees this field on 429s,
        but a defensive default keeps us from infinite looping if the
        body is unexpectedly empty.
        """
        try:
            body = response.json()
        except ValueError:
            return _RETRY_AFTER_FALLBACK_SECONDS
        value = body.get("parameters", {}).get("retry_after")
        if isinstance(value, int | float) and value > 0:
            return float(value)
        return _RETRY_AFTER_FALLBACK_SECONDS
