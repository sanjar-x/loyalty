"""
Phase-4 regression tests for idempotent CDEK webhook-subscription sync.

CDEK never deduplicates and caps a client at 2 active subscriptions, so
``ensure_webhook_subscriptions`` must: create only genuinely-missing
``(type, url)`` pairs, no-op when they already exist, and refuse to
exceed the 2-subscription cap (reporting the skipped types).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.infrastructure.providers.cdek.webhook_subscriptions import (
    ensure_webhook_subscriptions,
)

pytestmark = pytest.mark.unit

_URL = "https://app.example.com/api/v1/webhooks/logistics"


class TestEnsureWebhookSubscriptions:
    @pytest.mark.asyncio
    async def test_creates_both_auto_types_when_none_exist(self) -> None:
        client = AsyncMock()
        client.list_webhooks.return_value = []

        result = await ensure_webhook_subscriptions(client, _URL)

        assert set(result.created) == {"ORDER_STATUS", "ORDER_MODIFIED"}
        assert result.already_present == ()
        assert result.not_created == ()
        assert client.create_webhook.await_count == 2

    @pytest.mark.asyncio
    async def test_idempotent_when_already_subscribed(self) -> None:
        client = AsyncMock()
        client.list_webhooks.return_value = [
            {"uuid": "1", "type": "ORDER_STATUS", "url": _URL},
            {"uuid": "2", "type": "ORDER_MODIFIED", "url": _URL},
        ]

        result = await ensure_webhook_subscriptions(client, _URL)

        assert result.created == ()
        assert set(result.already_present) == {"ORDER_STATUS", "ORDER_MODIFIED"}
        client.create_webhook.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_respects_two_subscription_cap(self) -> None:
        # Two unrelated subscriptions already occupy the cap — nothing
        # can be created, both requested types land in ``not_created``.
        client = AsyncMock()
        client.list_webhooks.return_value = [
            {"uuid": "1", "type": "PRINT_FORM", "url": "https://other"},
            {"uuid": "2", "type": "DELIV_PROBLEM", "url": "https://other"},
        ]

        result = await ensure_webhook_subscriptions(client, _URL)

        assert result.created == ()
        assert set(result.not_created) == {"ORDER_STATUS", "ORDER_MODIFIED"}
        client.create_webhook.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_creates_only_the_missing_type_within_cap(self) -> None:
        # One free slot, ORDER_STATUS already present for our URL.
        client = AsyncMock()
        client.list_webhooks.return_value = [
            {"uuid": "1", "type": "ORDER_STATUS", "url": _URL},
        ]

        result = await ensure_webhook_subscriptions(client, _URL)

        assert result.created == ("ORDER_MODIFIED",)
        assert result.already_present == ("ORDER_STATUS",)
        assert result.not_created == ()
        client.create_webhook.assert_awaited_once_with(_URL, "ORDER_MODIFIED")

    @pytest.mark.asyncio
    async def test_same_type_different_url_is_not_treated_as_present(self) -> None:
        # ORDER_STATUS exists but for a *different* URL — still missing
        # for ours, and one free slot is enough to register it.
        client = AsyncMock()
        client.list_webhooks.return_value = [
            {"uuid": "1", "type": "ORDER_STATUS", "url": "https://stale-url"},
        ]

        result = await ensure_webhook_subscriptions(client, _URL)

        # 1 existing → 1 free slot → only the first requested type fits.
        assert result.created == ("ORDER_STATUS",)
        assert result.not_created == ("ORDER_MODIFIED",)

    @pytest.mark.asyncio
    async def test_non_list_payload_is_treated_as_empty(self) -> None:
        client = AsyncMock()
        client.list_webhooks.return_value = {"unexpected": "shape"}

        result = await ensure_webhook_subscriptions(client, _URL)

        assert set(result.created) == {"ORDER_STATUS", "ORDER_MODIFIED"}
