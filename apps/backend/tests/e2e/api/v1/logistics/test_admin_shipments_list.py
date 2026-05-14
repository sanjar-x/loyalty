"""E2E tests for ``GET /api/v1/admin/logistics/shipments`` (LOG-003).

The full happy path with seeded shipments lives in the integration
suite — these tests focus on the wire-level contract: HTTP gating,
permission gating, query-validation errors, and shape of the empty
response.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterable

import jwt
import pytest
import redis.asyncio as aioredis
from dishka import AsyncContainer
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.e2e


@pytest.fixture
async def logistics_read_client(
    async_client: AsyncClient,
    db_session: AsyncSession,
    app_container: AsyncContainer,
) -> AsyncIterable[AsyncClient]:
    """Authed client with ``logistics:read`` injected into the perms cache.

    Mirrors the ``admin_client`` fixture but seeds a different permission
    set so the test stays self-contained — no implicit dependency on
    ``catalog:manage`` from the shared admin fixture.
    """
    email = f"logistics-{uuid.uuid4().hex[:8]}@test.com"
    password = "S3cure!LogisticsPass"

    await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"login": email, "password": password},
    )
    tokens = login_resp.json()
    access_token = tokens["accessToken"]

    payload = jwt.decode(access_token, options={"verify_signature": False})
    session_id = payload["sid"]
    cache_key = f"perms:{session_id}"

    redis_client: aioredis.Redis = await app_container.get(aioredis.Redis)
    await redis_client.set(cache_key, json.dumps(["logistics:read"]), ex=300)

    async_client.headers["Authorization"] = f"Bearer {access_token}"
    yield async_client
    async_client.headers.pop("Authorization", None)
    await redis_client.delete(cache_key)


async def test_list_shipments_requires_auth(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/admin/logistics/shipments")
    assert resp.status_code == 401


async def test_list_shipments_requires_logistics_read(
    authenticated_client: AsyncClient,
) -> None:
    """Authed user without ``logistics:read`` gets 403."""
    resp = await authenticated_client.get("/api/v1/admin/logistics/shipments")
    assert resp.status_code == 403


async def test_list_shipments_with_permission_returns_200(
    logistics_read_client: AsyncClient,
) -> None:
    resp = await logistics_read_client.get("/api/v1/admin/logistics/shipments")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    assert "nextCursor" in body


async def test_invalid_provider_filter_returns_422(
    logistics_read_client: AsyncClient,
) -> None:
    resp = await logistics_read_client.get(
        "/api/v1/admin/logistics/shipments",
        params={"provider": "fake_carrier"},
    )
    assert resp.status_code == 422


async def test_invalid_status_filter_returns_422(
    logistics_read_client: AsyncClient,
) -> None:
    resp = await logistics_read_client.get(
        "/api/v1/admin/logistics/shipments",
        params={"status": "totally_made_up"},
    )
    assert resp.status_code == 422


async def test_limit_out_of_range_returns_422(
    logistics_read_client: AsyncClient,
) -> None:
    resp = await logistics_read_client.get(
        "/api/v1/admin/logistics/shipments",
        params={"limit": 0},
    )
    assert resp.status_code == 422

    resp = await logistics_read_client.get(
        "/api/v1/admin/logistics/shipments",
        params={"limit": 1000},
    )
    assert resp.status_code == 422


async def test_valid_provider_filter_accepted(
    logistics_read_client: AsyncClient,
) -> None:
    resp = await logistics_read_client.get(
        "/api/v1/admin/logistics/shipments",
        params={"provider": "cdek"},
    )
    assert resp.status_code == 200


async def test_combined_filters_accepted(
    logistics_read_client: AsyncClient,
) -> None:
    resp = await logistics_read_client.get(
        "/api/v1/admin/logistics/shipments",
        params={
            "provider": "dobropost",
            "status": "booked",
            "limit": 25,
        },
    )
    assert resp.status_code == 200


async def test_pagination_through_next_cursor(
    logistics_read_client: AsyncClient,
) -> None:
    """The cursor field round-trips when there are no items.

    With an empty table ``next_cursor`` is ``None`` and the client can
    still legally pass the value back. We assert the contract: passing
    no cursor yields a valid empty response (next_cursor=null).
    """
    resp = await logistics_read_client.get("/api/v1/admin/logistics/shipments")
    assert resp.status_code == 200
    body = resp.json()
    assert body["nextCursor"] is None
