"""
E2E contract tests for pagination behavior across catalog endpoints (API-05).

Validates offset, limit, total, hasNext fields on PaginatedResponse for
normal pages, empty results, and boundary conditions.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import create_brand, create_category

pytestmark = pytest.mark.asyncio


class TestBrandsPagination:
    """Pagination behavior tests on GET /api/v1/catalog/brands."""

    async def test_brands_pagination_default_params(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await admin_client.get("/api/v1/catalog/brands")
        assert resp.status_code == 200
        data = resp.json()
        assert data["offset"] == 0
        assert data["limit"] == 50
        assert isinstance(data["total"], int)
        assert data["total"] >= 0
        assert isinstance(data["hasNext"], bool)
        assert isinstance(data["items"], list)

    async def test_brands_pagination_custom_offset_limit(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        # Create 3 brands to ensure enough data
        for _ in range(3):
            await create_brand(admin_client)
        resp = await admin_client.get(
            "/api/v1/catalog/brands", params={"offset": 1, "limit": 2}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["offset"] == 1
        assert data["limit"] == 2
        assert len(data["items"]) <= 2

    async def test_brands_pagination_offset_beyond_total(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        await create_brand(admin_client)
        resp = await admin_client.get(
            "/api/v1/catalog/brands", params={"offset": 1000, "limit": 10}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] >= 1  # Real total, items just empty

    async def test_brands_pagination_has_next_true(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        for _ in range(3):
            await create_brand(admin_client)
        resp = await admin_client.get(
            "/api/v1/catalog/brands", params={"offset": 0, "limit": 1}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hasNext"] is True

    async def test_brands_pagination_has_next_false(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        await create_brand(admin_client)
        resp = await admin_client.get(
            "/api/v1/catalog/brands", params={"offset": 0, "limit": 200}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hasNext"] is False


class TestProductsPagination:
    """Pagination behavior tests on GET /api/v1/catalog/products."""

    async def test_products_pagination_default_params(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await admin_client.get("/api/v1/catalog/products")
        assert resp.status_code == 200
        data = resp.json()
        assert data["offset"] == 0
        assert isinstance(data["total"], int)
        assert isinstance(data["hasNext"], bool)

    async def test_products_pagination_custom_limit(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        # Create 3 products
        for _ in range(3):
            brand = await create_brand(admin_client)
            cat = await create_category(admin_client)
            await admin_client.post(
                "/api/v1/catalog/products",
                json={
                    "titleI18n": {"ru": "Стр", "en": "Page"},
                    "slug": f"pag-{uuid.uuid4().hex[:8]}",
                    "brandId": str(brand["id"]),
                    "primaryCategoryId": str(cat["id"]),
                },
            )
        resp = await admin_client.get(
            "/api/v1/catalog/products", params={"limit": 2}
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2


class TestPaginationEdgeCases:
    """Edge case tests for pagination behavior."""

    async def test_pagination_empty_result(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await admin_client.get(
            "/api/v1/catalog/brands", params={"offset": 999999, "limit": 10}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert isinstance(data["total"], int)

    async def test_pagination_limit_max_boundary(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """limit=200 (max allowed) should not error."""
        resp = await admin_client.get(
            "/api/v1/catalog/brands", params={"limit": 200}
        )
        assert resp.status_code == 200

    async def test_pagination_limit_exceeds_max_returns_422(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """limit=201 exceeds le=200 validation -> 422."""
        resp = await admin_client.get(
            "/api/v1/catalog/brands", params={"limit": 201}
        )
        assert resp.status_code == 422
