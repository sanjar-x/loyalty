"""
E2E contract tests for Brand admin endpoints.

Validates HTTP status codes, camelCase response shapes, and error handling
for all brand CRUD and bulk endpoints through the full HTTP stack.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import create_brand

pytestmark = pytest.mark.asyncio


class TestBrandEndpoints:
    """Tests for /api/v1/catalog/brands endpoints."""

    # ── POST /brands ──

    async def test_create_brand_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        slug = f"nike-{uuid.uuid4().hex[:8]}"
        payload = {
            "name": "Nike",
            "slug": slug,
            "logoUrl": "https://cdn.example.com/nike.webp",
        }
        resp = await admin_client.post("/api/v1/catalog/brands", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data

    async def test_create_brand_duplicate_slug_returns_409(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        slug = f"dup-{uuid.uuid4().hex[:8]}"
        await admin_client.post(
            "/api/v1/catalog/brands", json={"name": "A", "slug": slug}
        )
        resp = await admin_client.post(
            "/api/v1/catalog/brands", json={"name": "B", "slug": slug}
        )
        assert resp.status_code == 409
        assert "error" in resp.json()

    async def test_create_brand_invalid_slug_returns_422(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await admin_client.post(
            "/api/v1/catalog/brands", json={"name": "X", "slug": "INVALID SLUG"}
        )
        assert resp.status_code == 422

    # ── POST /brands/bulk ──

    async def test_bulk_create_brands_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        items = [
            {"name": f"B{i}", "slug": f"bulk-b{i}-{uuid.uuid4().hex[:6]}"}
            for i in range(3)
        ]
        resp = await admin_client.post(
            "/api/v1/catalog/brands/bulk",
            json={"items": items, "skipExisting": False},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["createdCount"] == 3
        assert len(data["ids"]) == 3

    # ── GET /brands ──

    async def test_list_brands_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        await create_brand(admin_client)
        resp = await admin_client.get(
            "/api/v1/catalog/brands", params={"offset": 0, "limit": 10}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert "hasNext" in data
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert "id" in item
        assert "name" in item
        assert "slug" in item

    # ── GET /brands/{brand_id} ──

    async def test_get_brand_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_brand(admin_client)
        resp = await admin_client.get(f"/api/v1/catalog/brands/{created['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == created["id"]

    async def test_get_brand_not_found_returns_404(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        fake_id = str(uuid.uuid4())
        resp = await admin_client.get(f"/api/v1/catalog/brands/{fake_id}")
        assert resp.status_code == 404

    # ── PATCH /brands/{brand_id} ──

    async def test_update_brand_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_brand(admin_client)
        resp = await admin_client.patch(
            f"/api/v1/catalog/brands/{created['id']}", json={"name": "Updated"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    # ── DELETE /brands/{brand_id} ──

    async def test_delete_brand_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_brand(admin_client)
        resp = await admin_client.delete(f"/api/v1/catalog/brands/{created['id']}")
        assert resp.status_code == 204

    async def test_delete_brand_not_found_returns_404(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await admin_client.delete(f"/api/v1/catalog/brands/{uuid.uuid4()}")
        assert resp.status_code == 404
