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
