"""Integration tests for ``DobroPostHttpClient`` — respx-mocked HTTP.

Exercises the resiliency story end-to-end:

* sign-in token cache + 12h TTL
* 401 force-refresh path
* exponential-backoff retry on 429 / 5xx
* circuit-breaker opens after N consecutive failures
* PUT /api/shipment, DELETE, GET list happy paths
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from src.bootstrap.config import settings
from src.modules.order.domain.exceptions import CrossBorderProviderError
from src.modules.order.infrastructure.adapters.dobropost_client import (
    DobroPostHttpClient,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _dobropost_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject test creds + tighter retry knobs so tests stay fast."""
    monkeypatch.setattr(
        settings,
        "DOBROPOST_EMAIL",
        type(settings.DOBROPOST_EMAIL)("e2e@example.com"),
    )
    monkeypatch.setattr(
        settings,
        "DOBROPOST_PASSWORD",
        type(settings.DOBROPOST_PASSWORD)("hunter2"),
    )
    monkeypatch.setattr(settings, "DOBROPOST_BASE_URL", "https://dobropost.test")
    monkeypatch.setattr(settings, "DOBROPOST_RETRY_BACKOFF_BASE_SECONDS", 0.0)
    monkeypatch.setattr(settings, "DOBROPOST_RETRY_BACKOFF_MAX_SECONDS", 0.01)


# ---------------------------------------------------------------------------
# Sign-in
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(base_url="https://dobropost.test")
async def test_sign_in_caches_token(respx_mock: respx.MockRouter) -> None:
    sign_in = respx_mock.post("/api/shipment/sign-in").mock(
        return_value=httpx.Response(200, json={"token": "tok-abc"})
    )
    respx_mock.post("/api/shipment").mock(
        return_value=httpx.Response(200, json={"id": 42, "dpTrackNumber": "DP42"})
    )

    client = DobroPostHttpClient()
    await client.create_shipment({"foo": "bar"})
    await client.create_shipment({"foo": "baz"})  # second call reuses token

    assert sign_in.call_count == 1
    await client.aclose()


# ---------------------------------------------------------------------------
# 401 force refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(base_url="https://dobropost.test")
async def test_401_triggers_force_refresh(respx_mock: respx.MockRouter) -> None:
    tokens = iter(["expired-tok", "fresh-tok"])
    respx_mock.post("/api/shipment/sign-in").mock(
        side_effect=lambda req: httpx.Response(200, json={"token": next(tokens)})
    )
    calls: list[str] = []

    def _create(req: httpx.Request) -> httpx.Response:
        auth = req.headers.get("authorization", "")
        calls.append(auth)
        if auth == "Bearer expired-tok":
            return httpx.Response(401, json={"error": "expired"})
        return httpx.Response(200, json={"id": 7})

    respx_mock.post("/api/shipment").mock(side_effect=_create)

    client = DobroPostHttpClient()
    out = await client.create_shipment({"foo": "bar"})

    assert out["id"] == 7
    assert calls == ["Bearer expired-tok", "Bearer fresh-tok"]
    await client.aclose()


# ---------------------------------------------------------------------------
# Retry on 5xx
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(base_url="https://dobropost.test")
async def test_retry_on_5xx_then_success(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("/api/shipment/sign-in").mock(
        return_value=httpx.Response(200, json={"token": "tok"})
    )
    responses = iter(
        [
            httpx.Response(503, text="busy"),
            httpx.Response(502, text="bad gw"),
            httpx.Response(200, json={"id": 99, "dpTrackNumber": "DP99"}),
        ]
    )
    create_route = respx_mock.post("/api/shipment").mock(
        side_effect=lambda req: next(responses)
    )

    client = DobroPostHttpClient()
    out = await client.create_shipment({"foo": "bar"})

    assert out["id"] == 99
    assert create_route.call_count == 3
    await client.aclose()


@pytest.mark.asyncio
@respx.mock(base_url="https://dobropost.test")
async def test_exhausted_retries_raises_provider_error(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DOBROPOST_RETRY_MAX_ATTEMPTS", 2)
    respx_mock.post("/api/shipment/sign-in").mock(
        return_value=httpx.Response(200, json={"token": "tok"})
    )
    respx_mock.post("/api/shipment").mock(
        return_value=httpx.Response(503, text="permanent")
    )

    client = DobroPostHttpClient()
    with pytest.raises(CrossBorderProviderError):
        await client.create_shipment({"foo": "bar"})
    await client.aclose()


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(base_url="https://dobropost.test")
async def test_circuit_breaker_opens_after_threshold(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DOBROPOST_RETRY_MAX_ATTEMPTS", 1)
    monkeypatch.setattr(settings, "DOBROPOST_CIRCUIT_FAILURE_THRESHOLD", 2)
    respx_mock.post("/api/shipment/sign-in").mock(
        return_value=httpx.Response(200, json={"token": "tok"})
    )
    create_route = respx_mock.post("/api/shipment").mock(
        return_value=httpx.Response(500, text="boom")
    )

    client = DobroPostHttpClient()
    # Two failures trip the breaker.
    for _ in range(2):
        with pytest.raises(CrossBorderProviderError):
            await client.create_shipment({"foo": "bar"})
    # Third call short-circuits without hitting the network.
    with pytest.raises(CrossBorderProviderError) as excinfo:
        await client.create_shipment({"foo": "bar"})
    assert "circuit_open" in str(excinfo.value)
    assert create_route.call_count == 2
    await client.aclose()


# ---------------------------------------------------------------------------
# PUT / DELETE / GET happy paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(base_url="https://dobropost.test")
async def test_update_shipment_put(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("/api/shipment/sign-in").mock(
        return_value=httpx.Response(200, json={"token": "tok"})
    )
    captured: dict[str, Any] = {}

    def _put(req: httpx.Request) -> httpx.Response:
        captured["body"] = req.content
        return httpx.Response(200, json={"id": 42, "updated": True})

    respx_mock.put("/api/shipment").mock(side_effect=_put)
    client = DobroPostHttpClient()
    out = await client.update_shipment({"id": 42, "consignee": {}})
    assert out["updated"] is True
    assert b'"id":42' in captured["body"]
    await client.aclose()


@pytest.mark.asyncio
@respx.mock(base_url="https://dobropost.test")
async def test_delete_shipment(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("/api/shipment/sign-in").mock(
        return_value=httpx.Response(200, json={"token": "tok"})
    )
    delete_route = respx_mock.delete("/api/shipment/42").mock(
        return_value=httpx.Response(204)
    )
    client = DobroPostHttpClient()
    await client.delete_shipment(42)
    assert delete_route.call_count == 1
    await client.aclose()


@pytest.mark.asyncio
@respx.mock(base_url="https://dobropost.test")
async def test_list_shipments_with_status_filter(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.post("/api/shipment/sign-in").mock(
        return_value=httpx.Response(200, json={"token": "tok"})
    )
    list_route = respx_mock.get("/api/shipment").mock(
        return_value=httpx.Response(200, json={"items": [], "total": 0})
    )
    client = DobroPostHttpClient()
    out = await client.list_shipments(page=2, offset=10, status_id=649)
    assert out["total"] == 0
    request = list_route.calls.last.request
    assert "page=2" in str(request.url)
    assert "statusId=649" in str(request.url)
    await client.aclose()
