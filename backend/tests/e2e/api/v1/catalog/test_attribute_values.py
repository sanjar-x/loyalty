"""
E2E contract tests for AttributeValue admin endpoints.

Validates HTTP status codes, camelCase response shapes, and error handling
for all attribute value CRUD, activate/deactivate, and reorder endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import (
    create_attribute,
    create_attribute_value,
)

pytestmark = pytest.mark.asyncio


class TestAttributeValueEndpoints:
    """Tests for /api/v1/catalog/attributes/{id}/values endpoints."""

    # ── POST /attributes/{id}/values ──

    async def test_add_attribute_value_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        attr = await create_attribute(admin_client)
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "code": f"red_{suffix}",
            "slug": f"red-{suffix}",
            "valueI18n": {"ru": "Красный", "en": "Red"},
        }
        resp = await admin_client.post(
            f"/api/v1/catalog/attributes/{attr['id']}/values", json=payload
        )
        assert resp.status_code == 201
        assert "id" in resp.json()

    async def test_add_attribute_value_missing_locale_returns_422(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        attr = await create_attribute(admin_client)
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "code": f"bad_{suffix}",
            "slug": f"bad-{suffix}",
            "valueI18n": {"en": "Only English"},
        }
        resp = await admin_client.post(
            f"/api/v1/catalog/attributes/{attr['id']}/values", json=payload
        )
        assert resp.status_code == 422

    # ── POST /attributes/{id}/values/bulk ──

    async def test_bulk_add_attribute_values_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        attr = await create_attribute(admin_client)
        items = [
            {
                "code": f"bval{i}_{uuid.uuid4().hex[:6]}",
                "slug": f"bval{i}-{uuid.uuid4().hex[:6]}",
                "valueI18n": {"ru": f"Знач{i}", "en": f"Val{i}"},
            }
            for i in range(3)
        ]
        resp = await admin_client.post(
            f"/api/v1/catalog/attributes/{attr['id']}/values/bulk",
            json={"items": items},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["createdCount"] == 3

    # ── GET /attributes/{id}/values ──

    async def test_list_attribute_values_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        attr = await create_attribute(admin_client)
        await create_attribute_value(admin_client, attr["id"])
        resp = await admin_client.get(
            f"/api/v1/catalog/attributes/{attr['id']}/values",
            params={"offset": 0, "limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    # ── GET /attributes/{aid}/values/{vid} ──

    async def test_get_attribute_value_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        attr = await create_attribute(admin_client)
        val = await create_attribute_value(admin_client, attr["id"])
        resp = await admin_client.get(
            f"/api/v1/catalog/attributes/{attr['id']}/values/{val['id']}"
        )
        assert resp.status_code == 200
        data = resp.json()
        for field in (
            "id", "attributeId", "code", "slug", "valueI18n",
            "searchAliases", "metaData", "sortOrder", "isActive",
        ):
            assert field in data, f"Missing camelCase field: {field}"

    # ── PATCH /attributes/{aid}/values/{vid} ──

    async def test_update_attribute_value_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        attr = await create_attribute(admin_client)
        val = await create_attribute_value(admin_client, attr["id"])
        resp = await admin_client.patch(
            f"/api/v1/catalog/attributes/{attr['id']}/values/{val['id']}",
            json={"sortOrder": 5},
        )
        assert resp.status_code == 200

    # ── PATCH /attributes/{aid}/values/{vid}/deactivate ──

    async def test_deactivate_attribute_value_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        attr = await create_attribute(admin_client)
        val = await create_attribute_value(admin_client, attr["id"])
        resp = await admin_client.patch(
            f"/api/v1/catalog/attributes/{attr['id']}/values/{val['id']}/deactivate"
        )
        assert resp.status_code == 200
        assert resp.json()["isActive"] is False

    # ── PATCH /attributes/{aid}/values/{vid}/activate ──

    async def test_activate_attribute_value_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        attr = await create_attribute(admin_client)
        val = await create_attribute_value(admin_client, attr["id"])
        # Deactivate first
        await admin_client.patch(
            f"/api/v1/catalog/attributes/{attr['id']}/values/{val['id']}/deactivate"
        )
        # Then activate
        resp = await admin_client.patch(
            f"/api/v1/catalog/attributes/{attr['id']}/values/{val['id']}/activate"
        )
        assert resp.status_code == 200
        assert resp.json()["isActive"] is True

    # ── DELETE /attributes/{aid}/values/{vid} ──

    async def test_delete_attribute_value_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        attr = await create_attribute(admin_client)
        val = await create_attribute_value(admin_client, attr["id"])
        resp = await admin_client.delete(
            f"/api/v1/catalog/attributes/{attr['id']}/values/{val['id']}"
        )
        assert resp.status_code == 204

    # ── POST /attributes/{aid}/values/reorder ──

    async def test_reorder_attribute_values_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        attr = await create_attribute(admin_client)
        v1 = await create_attribute_value(admin_client, attr["id"])
        v2 = await create_attribute_value(admin_client, attr["id"])
        resp = await admin_client.post(
            f"/api/v1/catalog/attributes/{attr['id']}/values/reorder",
            json={
                "items": [
                    {"valueId": v2["id"], "sortOrder": 0},
                    {"valueId": v1["id"], "sortOrder": 1},
                ]
            },
        )
        assert resp.status_code == 204
