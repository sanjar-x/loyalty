"""
E2E contract tests for Product admin endpoints.

Validates HTTP status codes, camelCase response shapes, and error handling
for all product CRUD, status change, and completeness endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import (
    create_brand,
    create_category,
)

pytestmark = pytest.mark.asyncio


async def create_product(
    client: AsyncClient,
    brand_id: str,
    category_id: str,
    *,
    slug: str | None = None,
    title_i18n: dict[str, str] | None = None,
) -> dict:
    """Helper to create a product via API and return the response JSON."""
    slug = slug or f"prod-{uuid.uuid4().hex[:8]}"
    title_i18n = title_i18n or {"ru": "Товар", "en": "Product"}
    payload = {
        "titleI18n": title_i18n,
        "slug": slug,
        "brandId": str(brand_id),
        "primaryCategoryId": str(category_id),
    }
    resp = await client.post("/api/v1/catalog/products", json=payload)
    assert resp.status_code == 201, f"create_product failed: {resp.status_code} {resp.text}"
    return resp.json()


class TestProductEndpoints:
    """Tests for /api/v1/catalog/products endpoints."""

    # ── POST /products ──

    async def test_create_product_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        brand = await create_brand(admin_client)
        cat = await create_category(admin_client)
        data = await create_product(admin_client, brand["id"], cat["id"])
        assert "id" in data
        assert "defaultVariantId" in data
        assert "message" in data

    async def test_create_product_nonexistent_brand_returns_404(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        cat = await create_category(admin_client)
        resp = await admin_client.post(
            "/api/v1/catalog/products",
            json={
                "titleI18n": {"ru": "Тест", "en": "Test"},
                "slug": f"nob-{uuid.uuid4().hex[:8]}",
                "brandId": str(uuid.uuid4()),
                "primaryCategoryId": cat["id"],
            },
        )
        assert resp.status_code == 404

    async def test_create_product_duplicate_slug_returns_409(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        brand = await create_brand(admin_client)
        cat = await create_category(admin_client)
        slug = f"dup-{uuid.uuid4().hex[:8]}"
        await create_product(admin_client, brand["id"], cat["id"], slug=slug)
        resp = await admin_client.post(
            "/api/v1/catalog/products",
            json={
                "titleI18n": {"ru": "Дубль", "en": "Dup"},
                "slug": slug,
                "brandId": str(brand["id"]),
                "primaryCategoryId": str(cat["id"]),
            },
        )
        assert resp.status_code == 409

    # ── GET /products ──

    async def test_list_products_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        brand = await create_brand(admin_client)
        cat = await create_category(admin_client)
        await create_product(admin_client, brand["id"], cat["id"])
        resp = await admin_client.get(
            "/api/v1/catalog/products", params={"offset": 0, "limit": 10}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "hasNext" in data
        item = data["items"][0]
        for field in (
            "id", "slug", "titleI18n", "status", "brandId",
            "primaryCategoryId", "version", "createdAt", "updatedAt",
        ):
            assert field in item, f"Missing camelCase field: {field}"

    # ── GET /products/{id} ──

    async def test_get_product_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        brand = await create_brand(admin_client)
        cat = await create_category(admin_client)
        created = await create_product(admin_client, brand["id"], cat["id"])
        resp = await admin_client.get(
            f"/api/v1/catalog/products/{created['id']}"
        )
        assert resp.status_code == 200
        data = resp.json()
        for field in (
            "id", "slug", "titleI18n", "descriptionI18n", "status",
            "brandId", "primaryCategoryId", "tags", "version",
            "createdAt", "updatedAt", "variants", "attributes",
        ):
            assert field in data, f"Missing camelCase field: {field}"

    async def test_get_product_not_found_returns_404(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await admin_client.get(
            f"/api/v1/catalog/products/{uuid.uuid4()}"
        )
        assert resp.status_code == 404

    # ── PATCH /products/{id} ──

    async def test_update_product_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        brand = await create_brand(admin_client)
        cat = await create_category(admin_client)
        created = await create_product(admin_client, brand["id"], cat["id"])
        resp = await admin_client.patch(
            f"/api/v1/catalog/products/{created['id']}",
            json={"titleI18n": {"ru": "Обновленный", "en": "Updated"}},
        )
        assert resp.status_code == 200

    # ── DELETE /products/{id} ──

    async def test_delete_product_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        brand = await create_brand(admin_client)
        cat = await create_category(admin_client)
        created = await create_product(admin_client, brand["id"], cat["id"])
        resp = await admin_client.delete(
            f"/api/v1/catalog/products/{created['id']}"
        )
        assert resp.status_code == 204

    # ── PATCH /products/{id}/status ──

    async def test_change_product_status_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        brand = await create_brand(admin_client)
        cat = await create_category(admin_client)
        created = await create_product(admin_client, brand["id"], cat["id"])
        resp = await admin_client.patch(
            f"/api/v1/catalog/products/{created['id']}/status",
            json={"status": "enriching"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "enriching"

    async def test_change_product_status_invalid_transition_returns_422(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        brand = await create_brand(admin_client)
        cat = await create_category(admin_client)
        created = await create_product(admin_client, brand["id"], cat["id"])
        # draft -> published is not a valid direct transition
        resp = await admin_client.patch(
            f"/api/v1/catalog/products/{created['id']}/status",
            json={"status": "published"},
        )
        assert resp.status_code == 422

    # ── GET /products/{id}/completeness ──

    async def test_get_product_completeness(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        brand = await create_brand(admin_client)
        cat = await create_category(admin_client)
        created = await create_product(admin_client, brand["id"], cat["id"])
        resp = await admin_client.get(
            f"/api/v1/catalog/products/{created['id']}/completeness"
        )
        assert resp.status_code == 200
        data = resp.json()
        for field in (
            "isComplete", "totalRequired", "filledRequired",
            "totalRecommended", "filledRecommended",
            "missingRequired", "missingRecommended",
        ):
            assert field in data, f"Missing camelCase field: {field}"
