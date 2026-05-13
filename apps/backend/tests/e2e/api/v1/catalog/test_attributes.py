"""
E2E contract tests for Attribute admin endpoints.

Validates HTTP status codes, camelCase response shapes, and error handling
for all attribute CRUD, bulk, and usage endpoints through the full HTTP stack.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import create_attribute

pytestmark = pytest.mark.asyncio


class TestAttributeEndpoints:
    """Tests for /api/v1/catalog/attributes endpoints."""

    # ── POST /attributes ──

    async def test_create_attribute_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "code": f"color_{suffix}",
            "slug": f"color-{suffix}",
            "nameI18N": {"ru": "Цвет", "en": "Color"},
            "dataType": "string",
            "uiType": "dropdown",
            "isDictionary": True,
            "level": "product",
        }
        resp = await admin_client.post("/api/v1/catalog/attributes", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data

    async def test_create_attribute_invalid_data_type_returns_422(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "code": f"bad_{suffix}",
            "slug": f"bad-{suffix}",
            "nameI18N": {"ru": "Плохой", "en": "Bad"},
            "dataType": "invalid_type",
            "uiType": "dropdown",
        }
        resp = await admin_client.post("/api/v1/catalog/attributes", json=payload)
        assert resp.status_code == 422

    # ── POST /attributes/bulk ──

    async def test_bulk_create_attributes_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        items = [
            {
                "code": f"bulk_a{i}_{uuid.uuid4().hex[:6]}",
                "slug": f"bulk-a{i}-{uuid.uuid4().hex[:6]}",
                "nameI18N": {"ru": f"Атр{i}", "en": f"Attr{i}"},
                "dataType": "string",
                "uiType": "dropdown",
            }
            for i in range(3)
        ]
        resp = await admin_client.post(
            "/api/v1/catalog/attributes/bulk",
            json={"items": items, "skipExisting": False},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["createdCount"] == 3

    # ── GET /attributes ──

    async def test_list_attributes_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        await create_attribute(admin_client)
        resp = await admin_client.get(
            "/api/v1/catalog/attributes", params={"offset": 0, "limit": 10}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert "hasNext" in data

    # ── GET /attributes/{id} ──

    async def test_get_attribute_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_attribute(admin_client)
        resp = await admin_client.get(f"/api/v1/catalog/attributes/{created['id']}")
        assert resp.status_code == 200
        data = resp.json()
        for field in (
            "id",
            "code",
            "slug",
            "nameI18N",
            "dataType",
            "uiType",
            "isDictionary",
            "level",
            "isFilterable",
            "isSearchable",
            "searchWeight",
            "isComparable",
            "isVisibleOnCard",
        ):
            assert field in data, f"Missing camelCase field: {field}"

    async def test_get_attribute_not_found_returns_404(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await admin_client.get(f"/api/v1/catalog/attributes/{uuid.uuid4()}")
        assert resp.status_code == 404

    # ── PATCH /attributes/{id} ──

    async def test_update_attribute_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_attribute(admin_client)
        resp = await admin_client.patch(
            f"/api/v1/catalog/attributes/{created['id']}",
            json={"isFilterable": True},
        )
        assert resp.status_code == 200

    # ── DELETE /attributes/{id} ──

    async def test_delete_attribute_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_attribute(admin_client)
        resp = await admin_client.delete(f"/api/v1/catalog/attributes/{created['id']}")
        assert resp.status_code == 204

    # ── GET /attributes/{id}/usage ──

    async def test_get_attribute_usage_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_attribute(admin_client)
        resp = await admin_client.get(
            f"/api/v1/catalog/attributes/{created['id']}/usage"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "templateCount" in data
        assert "categoryCount" in data
        assert "productCount" in data


class TestAttributeSchemaFixes:
    """Tests for attribute description_i18n optional fix."""

    async def test_create_attribute_without_description(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """POST /attributes with minimal required fields, NO descriptionI18N -> 201."""
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "code": f"color_{suffix}",
            "slug": f"color-{suffix}",
            "nameI18N": {"ru": "Цвет", "en": "Color"},
            "dataType": "string",
            "uiType": "dropdown",
            "isDictionary": True,
            "level": "product",
        }
        resp = await admin_client.post("/api/v1/catalog/attributes", json=payload)
        assert resp.status_code == 201
