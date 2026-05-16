"""E2E smoke tests for the Order/Payment APIs.

The full happy path (cart → snapshot → order → payment → capture →
shipment events → completion) requires populated catalog/supplier/cart
fixtures that exist only in the dedicated e2e harness for those
modules. These smoke tests focus on the new endpoints' wiring and
auth gating; richer flows are added once cart e2e fixtures expose a
``frozen_cart_with_snapshot`` builder.
"""

import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.e2e


async def test_create_order_requires_auth(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/api/v1/orders",
        json={
            "cartId": str(uuid.uuid4()),
            "snapshotId": str(uuid.uuid4()),
            "idempotencyKey": "idemp-e2e-12345",
        },
    )
    assert resp.status_code == 401


async def test_get_order_requires_auth(async_client: AsyncClient) -> None:
    resp = await async_client.get(f"/api/v1/orders/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_buy_now_requires_auth(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/api/v1/orders/buy-now",
        json={
            "skuId": str(uuid.uuid4()),
            "quantity": 1,
            "recipientId": str(uuid.uuid4()),
            "pickupCarrier": "cdek",
            "pickupPointId": "MSK-1",
            "idempotencyKey": "buy-now-e2e-12345",
        },
    )
    assert resp.status_code == 401


async def test_buy_now_with_missing_sku_returns_4xx(
    authenticated_client: AsyncClient,
) -> None:
    """Authenticated request reaches the handler; unknown SKU → 422."""
    resp = await authenticated_client.post(
        "/api/v1/orders/buy-now",
        json={
            "skuId": str(uuid.uuid4()),
            "quantity": 1,
            "recipientId": str(uuid.uuid4()),
            "pickupCarrier": "cdek",
            "pickupPointId": "MSK-1",
            "idempotencyKey": "buy-now-e2e-missing-sku",
        },
    )
    # BUY_NOW_SKU_NOT_FOUND → 422; recipient lookup also returns 422
    # for an unknown id. Either order of validation is acceptable.
    assert resp.status_code == 422


async def test_buy_now_rejects_invalid_quantity(
    authenticated_client: AsyncClient,
) -> None:
    """Pydantic ge=1 le=99 — quantity=0 is rejected before the handler."""
    resp = await authenticated_client.post(
        "/api/v1/orders/buy-now",
        json={
            "skuId": str(uuid.uuid4()),
            "quantity": 0,
            "recipientId": str(uuid.uuid4()),
            "pickupCarrier": "cdek",
            "pickupPointId": "MSK-1",
            "idempotencyKey": "buy-now-e2e-bad-qty",
        },
    )
    assert resp.status_code == 422


async def test_initiate_payment_requires_auth(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post(
        f"/api/v1/orders/{uuid.uuid4()}/payments",
        json={"idempotencyKey": "idemp-e2e-12345", "provider": "fake"},
    )
    assert resp.status_code == 401


async def test_cancel_order_requires_auth(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        f"/api/v1/orders/{uuid.uuid4()}/cancel",
        json={"reason": "customer_request", "idempotencyKey": "idemp-cancel"},
    )
    assert resp.status_code == 401


async def test_create_order_with_missing_snapshot_returns_4xx(
    authenticated_client: AsyncClient,
) -> None:
    """Authenticated request hits the handler; snapshot is missing → 422."""
    resp = await authenticated_client.post(
        "/api/v1/orders",
        json={
            "cartId": str(uuid.uuid4()),
            "snapshotId": str(uuid.uuid4()),
            "idempotencyKey": "idemp-e2e-missing-snap",
        },
    )
    # OrderEmptyError → 422
    assert resp.status_code in (404, 422)


async def test_simulate_capture_requires_auth(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post(
        f"/api/v1/payments/intents/{uuid.uuid4()}/_simulate-capture",
        json={"idempotencyKey": "idemp-cap"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# C5.2 — cancellation-reasons meta endpoint (auth gating only;
# happy-path is asserted at the unit level — see
# tests/unit/modules/order/test_cancellation_reasons_meta.py)
# ---------------------------------------------------------------------------


async def test_cancellation_reasons_meta_requires_auth(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get("/api/v1/admin/orders/_meta/cancellation-reasons")
    assert resp.status_code == 401
