"""
E2E contract tests for authorization enforcement across all catalog endpoints (API-03).

Tests two categories:
1. Unauthenticated (401): requests without Bearer token
2. Unauthorized (403): requests with valid JWT but missing catalog:manage permission
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class TestUnauthenticatedAccess:
    """Verify 401 for requests without auth header on protected endpoints."""

    async def test_unauthenticated_request_returns_401(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """POST /catalog/brands without Bearer token -> 401."""
        resp = await async_client.post(
            "/api/v1/catalog/brands",
            json={"name": "NoAuth", "slug": "noauth"},
        )
        assert resp.status_code == 401

    async def test_unauthenticated_brand_list_returns_401(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """GET /catalog/brands without Bearer token -> 401."""
        resp = await async_client.get("/api/v1/catalog/brands")
        assert resp.status_code == 401

    async def test_unauthenticated_product_create_returns_401(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """POST /catalog/products without Bearer token -> 401."""
        resp = await async_client.post(
            "/api/v1/catalog/products",
            json={
                "titleI18N": {"ru": "Тест", "en": "Test"},
                "slug": "noauth-prod",
                "brandId": str(uuid.uuid4()),
                "primaryCategoryId": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 401

    async def test_unauthenticated_category_delete_returns_401(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """DELETE /catalog/categories/{uuid} without Bearer token -> 401."""
        resp = await async_client.delete(f"/api/v1/catalog/categories/{uuid.uuid4()}")
        assert resp.status_code == 401


class TestUnauthorizedAccess:
    """Verify 403 for requests with valid JWT but without catalog:manage permission."""

    async def test_missing_permission_returns_403(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """POST /catalog/brands with auth but no catalog:manage -> 403."""
        resp = await authenticated_client.post(
            "/api/v1/catalog/brands",
            json={"name": "NoPerms", "slug": "noperms"},
        )
        assert resp.status_code == 403

    async def test_missing_permission_product_create_returns_403(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """POST /catalog/products with auth but no catalog:manage -> 403."""
        resp = await authenticated_client.post(
            "/api/v1/catalog/products",
            json={
                "titleI18N": {"ru": "Тест", "en": "Test"},
                "slug": "noperms-prod",
                "brandId": str(uuid.uuid4()),
                "primaryCategoryId": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 403

    async def test_missing_permission_attribute_create_returns_403(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """POST /catalog/attributes with auth but no catalog:manage -> 403."""
        resp = await authenticated_client.post(
            "/api/v1/catalog/attributes",
            json={
                "code": "noperms",
                "slug": "noperms",
                "nameI18N": {"ru": "Тест", "en": "Test"},
                "dataType": "string",
                "uiType": "dropdown",
            },
        )
        assert resp.status_code == 403

    async def test_missing_permission_sku_create_returns_403(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """POST /catalog/products/{uuid}/variants/{uuid}/skus with auth but no perm -> 403."""
        resp = await authenticated_client.post(
            f"/api/v1/catalog/products/{uuid.uuid4()}/variants/{uuid.uuid4()}/skus",
            json={
                "skuCode": "NOPERMS-SKU",
                "priceAmount": 1000,
                "priceCurrency": "RUB",
            },
        )
        assert resp.status_code == 403

    async def test_missing_permission_media_create_returns_403(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """POST /catalog/products/{uuid}/media with auth but no catalog:manage -> 403."""
        resp = await authenticated_client.post(
            f"/api/v1/catalog/products/{uuid.uuid4()}/media",
            json={
                "isExternal": True,
                "url": "https://example.com/noperms.jpg",
                "mediaType": "image",
                "role": "gallery",
                "sortOrder": 0,
            },
        )
        assert resp.status_code == 403
