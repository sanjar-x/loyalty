"""Contract tests for :class:`TelegramAlerter` (HARD-2).

Stubs httpx via ``MockTransport`` so the alerter's HTTP code path is
exercised end-to-end without touching the real Telegram Bot API. We
care about three properties:

* No-op when env vars are unset (must NOT raise, must NOT touch HTTP).
* 200 → True; non-200 (other than 429) → False with no retry.
* 429 → honour ``retry_after`` once, then either True (recovery) or
  False (still failing).
"""

from __future__ import annotations

import httpx
import pytest

from src.shared.infrastructure.alerts.telegram_alerter import TelegramAlerter

pytestmark = pytest.mark.unit


# Capture the real ``httpx.AsyncClient`` once, before any monkeypatch
# can replace ``httpx.AsyncClient`` in the alerter module's namespace.
# Without this, the patched factory below would call the patched class
# instead of the real one and recurse forever.
_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _mock_transport(handler):
    """Wrap a request->Response handler in an httpx MockTransport."""
    return httpx.MockTransport(handler)


def _patched_factory(handler):
    """Build a callable that returns a real AsyncClient with our transport."""

    def factory(*_args, **_kwargs):
        return _REAL_ASYNC_CLIENT(transport=_mock_transport(handler))

    return factory


class TestNoOp:
    @pytest.mark.asyncio
    async def test_returns_false_when_token_missing(self):
        alerter = TelegramAlerter(bot_token="", chat_id="@anything")
        # Should never reach the HTTP layer — no transport configured.
        delivered = await alerter.send("test")
        assert delivered is False

    @pytest.mark.asyncio
    async def test_returns_false_when_chat_missing(self):
        alerter = TelegramAlerter(bot_token="abc", chat_id="")
        delivered = await alerter.send("test")
        assert delivered is False


class TestSuccess:
    @pytest.mark.asyncio
    async def test_200_returns_true(self, monkeypatch):
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json={"ok": True})

        monkeypatch.setattr(
            "src.shared.infrastructure.alerts.telegram_alerter.httpx.AsyncClient",
            _patched_factory(handler),
        )
        alerter = TelegramAlerter(bot_token="t0k", chat_id="@chan")
        delivered = await alerter.send("hello")
        assert delivered is True
        assert len(seen) == 1
        # Verify request shape — chat_id + text in JSON payload.
        body = seen[0].read()
        assert b'"chat_id":"@chan"' in body
        assert b'"text":"hello"' in body


class TestErrorPaths:
    @pytest.mark.asyncio
    async def test_500_returns_false_no_retry(self, monkeypatch):
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(500, text="boom")

        monkeypatch.setattr(
            "src.shared.infrastructure.alerts.telegram_alerter.httpx.AsyncClient",
            _patched_factory(handler),
        )
        alerter = TelegramAlerter(bot_token="t0k", chat_id="@chan")
        delivered = await alerter.send("hello")
        assert delivered is False
        assert call_count == 1  # no retry on non-429

    @pytest.mark.asyncio
    async def test_transport_error_returns_false(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("simulated")

        monkeypatch.setattr(
            "src.shared.infrastructure.alerts.telegram_alerter.httpx.AsyncClient",
            _patched_factory(handler),
        )
        alerter = TelegramAlerter(bot_token="t0k", chat_id="@chan")
        delivered = await alerter.send("hello")
        assert delivered is False


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_429_then_200_succeeds(self, monkeypatch):
        responses = iter(
            [
                httpx.Response(
                    429, json={"ok": False, "parameters": {"retry_after": 0}}
                ),
                httpx.Response(200, json={"ok": True}),
            ]
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return next(responses)

        monkeypatch.setattr(
            "src.shared.infrastructure.alerts.telegram_alerter.httpx.AsyncClient",
            _patched_factory(handler),
        )
        alerter = TelegramAlerter(bot_token="t0k", chat_id="@chan")
        delivered = await alerter.send("hello")
        assert delivered is True

    @pytest.mark.asyncio
    async def test_429_twice_still_returns_false(self, monkeypatch):
        # Second 429 hits the non-retry branch → False, no infinite loop.
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(
                429, json={"ok": False, "parameters": {"retry_after": 0}}
            )

        monkeypatch.setattr(
            "src.shared.infrastructure.alerts.telegram_alerter.httpx.AsyncClient",
            _patched_factory(handler),
        )
        alerter = TelegramAlerter(bot_token="t0k", chat_id="@chan")
        delivered = await alerter.send("hello")
        assert delivered is False
        assert call_count == 2  # one retry, then give up

    def test_retry_after_extraction_with_value(self):
        response = httpx.Response(
            429, json={"ok": False, "parameters": {"retry_after": 5}}
        )
        assert TelegramAlerter._extract_retry_after(response) == 5.0

    def test_retry_after_fallback_when_missing(self):
        response = httpx.Response(429, json={"ok": False})
        assert TelegramAlerter._extract_retry_after(response) == 1.0

    def test_retry_after_fallback_when_body_not_json(self):
        response = httpx.Response(429, text="not json")
        assert TelegramAlerter._extract_retry_after(response) == 1.0
