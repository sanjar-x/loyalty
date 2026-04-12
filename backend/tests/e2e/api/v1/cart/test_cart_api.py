"""E2E tests for Cart API — HTTP round-trips through the full stack."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.e2e


async def test_anonymous_token_creation(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Generate anonymous cart token."""
    resp = await async_client.post("/api/v1/cart/anonymous-token")
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert len(data["token"]) > 0


async def test_get_cart_empty_anonymous(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Get cart for anonymous user — should return empty or 404."""
    token_resp = await async_client.post("/api/v1/cart/anonymous-token")
    token = token_resp.json()["token"]

    resp = await async_client.get(
        "/api/v1/cart",
        headers={"X-Anonymous-Token": token},
    )
    # Empty cart may return 404 or empty cart depending on implementation
    assert resp.status_code in (200, 404)


async def test_add_item_requires_valid_sku(
    authenticated_client: AsyncClient,
) -> None:
    """Adding a non-existent SKU should fail."""
    resp = await authenticated_client.post(
        "/api/v1/cart/items",
        json={"skuId": str(uuid.uuid4())},
    )
    # Should fail with 404 (SKU not found) or 422
    assert resp.status_code in (404, 422, 400)


async def test_checkout_requires_auth(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Checkout endpoints require authentication."""
    resp = await async_client.post(
        "/api/v1/cart/checkout",
        json={"pickupPointId": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


async def test_merge_requires_auth(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Merge endpoint requires authentication."""
    resp = await async_client.post(
        "/api/v1/cart/merge",
        json={"anonymousToken": "some-token"},
    )
    assert resp.status_code == 401


async def test_cancel_checkout_requires_auth(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Cancel checkout requires authentication."""
    resp = await async_client.post("/api/v1/cart/checkout/cancel")
    assert resp.status_code == 401
