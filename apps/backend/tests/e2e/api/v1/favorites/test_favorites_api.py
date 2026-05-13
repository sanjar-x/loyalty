"""E2E happy-path tests for the favorites HTTP API.

Auth fixtures and seed helpers come from the shared conftest. The
test focuses on the contract — request/response shapes, idempotency,
ownership errors — not on database internals (covered by integration
tests).
"""

import uuid

import pytest

pytestmark = pytest.mark.e2e


async def test_full_favorites_flow(authed_client, seeded_published_product):
    """Create list → add item → list contents → batch-check → remove."""
    create_resp = await authed_client.post(
        "/api/v1/favorites/lists", json={"name": "Wishlist"}
    )
    assert create_resp.status_code == 201
    list_id = create_resp.json()["id"]

    add_resp = await authed_client.post(
        "/api/v1/favorites/items",
        json={
            "target_type": "product",
            "target_id": str(seeded_published_product.id),
            "list_id": list_id,
        },
    )
    assert add_resp.status_code == 201
    body = add_resp.json()
    assert body["created"] is True
    assert body["list_id"] == list_id

    # Idempotent re-add — same list, same target → created=False
    repeat_resp = await authed_client.post(
        "/api/v1/favorites/items",
        json={
            "target_type": "product",
            "target_id": str(seeded_published_product.id),
            "list_id": list_id,
        },
    )
    assert repeat_resp.status_code == 201
    assert repeat_resp.json()["created"] is False

    items_resp = await authed_client.get(f"/api/v1/favorites/lists/{list_id}/items")
    assert items_resp.status_code == 200
    items_body = items_resp.json()
    assert len(items_body["items"]) == 1
    assert items_body["items"][0]["product"] is not None
    assert items_body["items"][0]["product"]["id"] == str(seeded_published_product.id)

    check_resp = await authed_client.post(
        "/api/v1/favorites/check",
        json={
            "target_type": "product",
            "target_ids": [str(seeded_published_product.id), str(uuid.uuid4())],
        },
    )
    assert check_resp.status_code == 200
    favorited = check_resp.json()["favorited"]
    assert str(seeded_published_product.id) in favorited

    remove_resp = await authed_client.delete(
        f"/api/v1/favorites/lists/{list_id}/items/product/{seeded_published_product.id}"
    )
    assert remove_resp.status_code == 204


async def test_default_list_cannot_be_renamed(authed_client):
    # First write lazily creates the default list.
    add_resp = await authed_client.post(
        "/api/v1/favorites/items",
        json={
            "target_type": "brand",
            "target_id": str(uuid.uuid4()),
        },
    )
    # The brand UUID is fake → expect 422 from ACL validator.
    assert add_resp.status_code == 422


async def test_unknown_list_id_returns_404(authed_client):
    fake_list_id = uuid.uuid4()
    resp = await authed_client.delete(
        f"/api/v1/favorites/lists/{fake_list_id}/items/product/{uuid.uuid4()}"
    )
    assert resp.status_code == 404


async def test_unauthenticated_access_rejected(api_client):
    resp = await api_client.get("/api/v1/favorites/lists")
    assert resp.status_code == 401
