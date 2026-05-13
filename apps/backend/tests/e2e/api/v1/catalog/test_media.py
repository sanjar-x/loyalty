"""
E2E contract tests for Product Media asset endpoints.

Uses external media (isExternal=true with URL) to bypass ImageBackend dependency.
Validates HTTP status codes, camelCase response shapes, and error handling
for all media CRUD and reorder endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import create_brand, create_category

pytestmark = pytest.mark.asyncio


async def _create_product(client: AsyncClient) -> str:
    """Helper: create brand + category + product, return product_id."""
    brand = await create_brand(client)
    cat = await create_category(client)
    resp = await client.post(
        "/api/v1/catalog/products",
        json={
            "titleI18N": {"ru": "Медиа тест", "en": "Media test"},
            "slug": f"media-prod-{uuid.uuid4().hex[:8]}",
            "brandId": str(brand["id"]),
            "primaryCategoryId": str(cat["id"]),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestMediaEndpoints:
    """Tests for /api/v1/catalog/products/{pid}/media endpoints."""

    # ── POST /products/{pid}/media ──

    async def test_add_external_media_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        product_id = await _create_product(admin_client)
        resp = await admin_client.post(
            f"/api/v1/catalog/products/{product_id}/media",
            json={
                "isExternal": True,
                "url": "https://example.com/photo.jpg",
                "mediaType": "image",
                "role": "gallery",
                "sortOrder": 0,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "message" in data

    async def test_add_media_validation_error_returns_422(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        product_id = await _create_product(admin_client)
        # isExternal=true but no URL -> validation error
        resp = await admin_client.post(
            f"/api/v1/catalog/products/{product_id}/media",
            json={
                "isExternal": True,
                "mediaType": "image",
                "role": "gallery",
                "sortOrder": 0,
            },
        )
        assert resp.status_code == 422

    # ── GET /products/{pid}/media ──

    async def test_list_media_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        product_id = await _create_product(admin_client)
        await admin_client.post(
            f"/api/v1/catalog/products/{product_id}/media",
            json={
                "isExternal": True,
                "url": "https://example.com/list.jpg",
                "mediaType": "image",
                "role": "gallery",
                "sortOrder": 0,
            },
        )
        resp = await admin_client.get(
            f"/api/v1/catalog/products/{product_id}/media",
            params={"offset": 0, "limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        item = data["items"][0]
        for field in (
            "id",
            "productId",
            "mediaType",
            "role",
            "sortOrder",
            "isExternal",
            "url",
        ):
            assert field in item, f"Missing camelCase field: {field}"

    # ── PATCH /products/{pid}/media/{mid} ──

    async def test_update_media_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        product_id = await _create_product(admin_client)
        add_resp = await admin_client.post(
            f"/api/v1/catalog/products/{product_id}/media",
            json={
                "isExternal": True,
                "url": "https://example.com/update.jpg",
                "mediaType": "image",
                "role": "gallery",
                "sortOrder": 0,
            },
        )
        media_id = add_resp.json()["id"]
        resp = await admin_client.patch(
            f"/api/v1/catalog/products/{product_id}/media/{media_id}",
            json={"role": "main"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "message" in data

    # ── DELETE /products/{pid}/media/{mid} ──

    async def test_delete_media_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        product_id = await _create_product(admin_client)
        add_resp = await admin_client.post(
            f"/api/v1/catalog/products/{product_id}/media",
            json={
                "isExternal": True,
                "url": "https://example.com/delete.jpg",
                "mediaType": "image",
                "role": "gallery",
                "sortOrder": 0,
            },
        )
        media_id = add_resp.json()["id"]
        resp = await admin_client.delete(
            f"/api/v1/catalog/products/{product_id}/media/{media_id}"
        )
        assert resp.status_code == 204

    # ── POST /products/{pid}/media/reorder ──

    async def test_reorder_media_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        product_id = await _create_product(admin_client)
        m1 = await admin_client.post(
            f"/api/v1/catalog/products/{product_id}/media",
            json={
                "isExternal": True,
                "url": "https://example.com/first.jpg",
                "mediaType": "image",
                "role": "gallery",
                "sortOrder": 0,
            },
        )
        m2 = await admin_client.post(
            f"/api/v1/catalog/products/{product_id}/media",
            json={
                "isExternal": True,
                "url": "https://example.com/second.jpg",
                "mediaType": "image",
                "role": "gallery",
                "sortOrder": 1,
            },
        )
        resp = await admin_client.post(
            f"/api/v1/catalog/products/{product_id}/media/reorder",
            json={
                "items": [
                    {"mediaId": m2.json()["id"], "sortOrder": 0},
                    {"mediaId": m1.json()["id"], "sortOrder": 1},
                ]
            },
        )
        assert resp.status_code == 204
