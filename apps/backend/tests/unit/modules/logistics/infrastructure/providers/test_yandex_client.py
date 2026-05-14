"""
Regression tests for ``YandexDeliveryClient`` request shaping.

- ``get_requests_info`` sends ``request_ids`` as a JSON array — the
  documented ``string[]`` type — not a comma-joined string.
- ``pricing_calculator`` forwards the optional ``is_oversized`` (КГТ)
  query flag only when an explicit value is supplied.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from src.modules.logistics.infrastructure.providers.yandex_delivery.client import (
    YandexDeliveryClient,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mocked_client() -> tuple[YandexDeliveryClient, Any]:
    """A real client with its HTTP layer swapped for an ``AsyncMock``.

    Returns the client paired with the mocked ``request`` callable, so a
    test inspects call arguments through that handle instead of reaching
    back through the client's private ``_provider_client``. ``request``
    resolves to a stub response exposing a synchronous ``.json()`` —
    matching the real ``httpx.Response`` shape the typed client methods
    consume.
    """
    client = YandexDeliveryClient(base_url="https://test", oauth_token="token")
    provider_client = AsyncMock()
    response = Mock()
    response.json.return_value = {}
    provider_client.request.return_value = response
    client._provider_client = provider_client
    return client, provider_client.request


class TestGetRequestsInfo:
    @pytest.mark.asyncio
    async def test_sends_request_ids_as_array(
        self, mocked_client: tuple[YandexDeliveryClient, Any]
    ) -> None:
        client, request = mocked_client
        await client.get_requests_info(["req-1", "req-2", "req-3"])

        assert request.await_args.kwargs["json"] == {
            "request_ids": ["req-1", "req-2", "req-3"]
        }

    @pytest.mark.asyncio
    async def test_empty_list_stays_a_list(
        self, mocked_client: tuple[YandexDeliveryClient, Any]
    ) -> None:
        client, request = mocked_client
        await client.get_requests_info([])

        assert request.await_args.kwargs["json"] == {"request_ids": []}


class TestPricingCalculatorIsOversized:
    @pytest.mark.asyncio
    async def test_forwards_is_oversized_true(
        self, mocked_client: tuple[YandexDeliveryClient, Any]
    ) -> None:
        client, request = mocked_client
        await client.pricing_calculator({"total_weight": 1}, is_oversized=True)

        assert request.await_args.kwargs["params"] == {"is_oversized": "true"}

    @pytest.mark.asyncio
    async def test_forwards_is_oversized_false(
        self, mocked_client: tuple[YandexDeliveryClient, Any]
    ) -> None:
        client, request = mocked_client
        await client.pricing_calculator({"total_weight": 1}, is_oversized=False)

        assert request.await_args.kwargs["params"] == {"is_oversized": "false"}

    @pytest.mark.asyncio
    async def test_omits_param_when_unset(
        self, mocked_client: tuple[YandexDeliveryClient, Any]
    ) -> None:
        client, request = mocked_client
        await client.pricing_calculator({"total_weight": 1})

        assert request.await_args.kwargs["params"] is None
