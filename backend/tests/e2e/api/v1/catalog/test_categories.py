"""
E2E contract tests for Category admin endpoints.

Validates HTTP status codes, camelCase response shapes, and error handling
for all category CRUD, tree, and bulk endpoints through the full HTTP stack.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import create_category

pytestmark = pytest.mark.asyncio


class TestCategoryEndpoints:
    """Tests for /api/v1/catalog/categories endpoints."""

    # ── POST /categories ──

    async def test_create_category_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        payload = {
            "nameI18n": {"ru": "Обувь", "en": "Shoes"},
            "slug": f"shoes-{uuid.uuid4().hex[:8]}",
        }
        resp = await admin_client.post("/api/v1/catalog/categories", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "message" in data

    async def test_create_category_missing_locale_returns_422(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await admin_client.post(
            "/api/v1/catalog/categories",
            json={
                "nameI18n": {"en": "Only English"},
                "slug": f"bad-{uuid.uuid4().hex[:8]}",
            },
        )
        assert resp.status_code == 422

    async def test_create_category_with_parent(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        parent = await create_category(admin_client)
        child_resp = await admin_client.post(
            "/api/v1/catalog/categories",
            json={
                "nameI18n": {"ru": "Ребенок", "en": "Child"},
                "slug": f"child-{uuid.uuid4().hex[:8]}",
                "parentId": parent["id"],
            },
        )
        assert child_resp.status_code == 201

    # ── POST /categories/bulk ──

    async def test_bulk_create_categories_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        items = [
            {
                "nameI18n": {"ru": f"Кат{i}", "en": f"Cat{i}"},
                "slug": f"bulk-cat{i}-{uuid.uuid4().hex[:6]}",
            }
            for i in range(3)
        ]
        resp = await admin_client.post(
            "/api/v1/catalog/categories/bulk", json={"items": items}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["createdCount"] == 3

    # ── GET /categories/tree ──

    async def test_get_category_tree_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        await create_category(admin_client)
        resp = await admin_client.get("/api/v1/catalog/categories/tree")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    # ── GET /categories ──

    async def test_list_categories_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        await create_category(admin_client)
        resp = await admin_client.get(
            "/api/v1/catalog/categories", params={"offset": 0, "limit": 10}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    # ── GET /categories/{id} ──

    async def test_get_category_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_category(admin_client)
        resp = await admin_client.get(f"/api/v1/catalog/categories/{created['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == created["id"]
        assert "nameI18n" in data
        assert "slug" in data
        assert "fullSlug" in data
        assert "level" in data

    # ── PATCH /categories/{id} ──

    async def test_update_category_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_category(admin_client)
        resp = await admin_client.patch(
            f"/api/v1/catalog/categories/{created['id']}",
            json={"sortOrder": 5},
        )
        assert resp.status_code == 200

    # ── DELETE /categories/{id} ──

    async def test_delete_category_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_category(admin_client)
        resp = await admin_client.delete(f"/api/v1/catalog/categories/{created['id']}")
        assert resp.status_code == 204
