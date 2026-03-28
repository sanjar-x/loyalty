"""
E2E contract tests for ProductVariant admin endpoints.

Validates HTTP status codes, camelCase response shapes, and error handling
for all variant CRUD endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import create_brand, create_category

pytestmark = pytest.mark.asyncio


async def _create_product(client: AsyncClient) -> dict:
    """Helper: create brand + category + product, return product response."""
    brand = await create_brand(client)
    cat = await create_category(client)
    slug = f"var-prod-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/catalog/products",
        json={
            "titleI18n": {"ru": "Вариант тест", "en": "Variant test"},
            "slug": slug,
            "brandId": str(brand["id"]),
            "primaryCategoryId": str(cat["id"]),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestVariantEndpoints:
    """Tests for /api/v1/catalog/products/{pid}/variants endpoints."""

    # ── POST /products/{pid}/variants ──

    async def test_add_variant_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        product = await _create_product(admin_client)
        resp = await admin_client.post(
            f"/api/v1/catalog/products/{product['id']}/variants",
            json={
                "nameI18n": {"ru": "Красный", "en": "Red"},
                "sortOrder": 1,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "message" in data

    async def test_add_variant_to_nonexistent_product_returns_404(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await admin_client.post(
            f"/api/v1/catalog/products/{uuid.uuid4()}/variants",
            json={
                "nameI18n": {"ru": "Тест", "en": "Test"},
                "sortOrder": 0,
            },
        )
        assert resp.status_code == 404

    # ── GET /products/{pid}/variants ──

    async def test_list_variants_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        product = await _create_product(admin_client)
        resp = await admin_client.get(
            f"/api/v1/catalog/products/{product['id']}/variants",
            params={"offset": 0, "limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        # Default variant should exist
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert "id" in item
        assert "nameI18n" in item
        assert "sortOrder" in item
        assert "skus" in item

    # ── PATCH /products/{pid}/variants/{vid} ──

    async def test_update_variant_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        product = await _create_product(admin_client)
        variant_id = product["defaultVariantId"]
        resp = await admin_client.patch(
            f"/api/v1/catalog/products/{product['id']}/variants/{variant_id}",
            json={"sortOrder": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "message" in data

    # ── DELETE /products/{pid}/variants/{vid} ──

    async def test_delete_variant_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        product = await _create_product(admin_client)
        # Create a second variant to delete (default might be protected)
        add_resp = await admin_client.post(
            f"/api/v1/catalog/products/{product['id']}/variants",
            json={
                "nameI18n": {"ru": "Удалить", "en": "ToDelete"},
                "sortOrder": 2,
            },
        )
        assert add_resp.status_code == 201
        variant_id = add_resp.json()["id"]
        resp = await admin_client.delete(
            f"/api/v1/catalog/products/{product['id']}/variants/{variant_id}"
        )
        assert resp.status_code == 204
