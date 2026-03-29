"""
E2E contract tests for AttributeTemplate and Binding admin endpoints.

Validates HTTP status codes, camelCase response shapes, and error handling
for all attribute template CRUD, clone, and binding endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import (
    bind_attribute_to_template,
    create_attribute,
    create_attribute_template,
)

pytestmark = pytest.mark.asyncio


class TestAttributeTemplateEndpoints:
    """Tests for /api/v1/catalog/attribute-templates endpoints."""

    # ── POST /attribute-templates ──

    async def test_create_template_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "code": f"tmpl_{suffix}",
            "nameI18n": {"ru": "Обувь", "en": "Footwear"},
        }
        resp = await admin_client.post(
            "/api/v1/catalog/attribute-templates", json=payload
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data

    # ── POST /attribute-templates/clone ──

    async def test_clone_template_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        source = await create_attribute_template(admin_client)
        suffix = uuid.uuid4().hex[:8]
        resp = await admin_client.post(
            "/api/v1/catalog/attribute-templates/clone",
            json={
                "sourceTemplateId": source["id"],
                "newCode": f"clone_{suffix}",
                "newNameI18n": {"ru": "Клон", "en": "Clone"},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "bindingsCopied" in data

    # ── GET /attribute-templates ──

    async def test_list_templates_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        await create_attribute_template(admin_client)
        resp = await admin_client.get(
            "/api/v1/catalog/attribute-templates",
            params={"offset": 0, "limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "hasNext" in data

    # ── GET /attribute-templates/{id} ──

    async def test_get_template_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_attribute_template(admin_client)
        resp = await admin_client.get(
            f"/api/v1/catalog/attribute-templates/{created['id']}"
        )
        assert resp.status_code == 200
        data = resp.json()
        for field in ("id", "code", "nameI18n", "descriptionI18n", "sortOrder"):
            assert field in data, f"Missing camelCase field: {field}"

    # ── PATCH /attribute-templates/{id} ──

    async def test_update_template_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_attribute_template(admin_client)
        resp = await admin_client.patch(
            f"/api/v1/catalog/attribute-templates/{created['id']}",
            json={"sortOrder": 10},
        )
        assert resp.status_code == 200

    # ── DELETE /attribute-templates/{id} ──

    async def test_delete_template_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_attribute_template(admin_client)
        resp = await admin_client.delete(
            f"/api/v1/catalog/attribute-templates/{created['id']}"
        )
        assert resp.status_code == 204


class TestTemplateBindingEndpoints:
    """Tests for /api/v1/catalog/attribute-templates/{id}/attributes endpoints."""

    # ── POST /{id}/attributes ──

    async def test_bind_attribute_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        tmpl = await create_attribute_template(admin_client)
        attr = await create_attribute(admin_client)
        resp = await admin_client.post(
            f"/api/v1/catalog/attribute-templates/{tmpl['id']}/attributes",
            json={
                "attributeId": attr["id"],
                "requirementLevel": "required",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "affectedCategoriesCount" in data

    # ── GET /{id}/attributes ──

    async def test_list_bindings_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        tmpl = await create_attribute_template(admin_client)
        attr = await create_attribute(admin_client)
        await bind_attribute_to_template(admin_client, tmpl["id"], attr["id"])
        resp = await admin_client.get(
            f"/api/v1/catalog/attribute-templates/{tmpl['id']}/attributes",
            params={"offset": 0, "limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    # ── PATCH /{tid}/attributes/{bid} ──

    async def test_update_binding_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        tmpl = await create_attribute_template(admin_client)
        attr = await create_attribute(admin_client)
        binding = await bind_attribute_to_template(
            admin_client, tmpl["id"], attr["id"]
        )
        resp = await admin_client.patch(
            f"/api/v1/catalog/attribute-templates/{tmpl['id']}/attributes/{binding['id']}",
            json={"requirementLevel": "required"},
        )
        assert resp.status_code == 200

    # ── DELETE /{tid}/attributes/{bid} ──

    async def test_unbind_attribute_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        tmpl = await create_attribute_template(admin_client)
        attr = await create_attribute(admin_client)
        binding = await bind_attribute_to_template(
            admin_client, tmpl["id"], attr["id"]
        )
        resp = await admin_client.delete(
            f"/api/v1/catalog/attribute-templates/{tmpl['id']}/attributes/{binding['id']}"
        )
        assert resp.status_code == 204

    # ── POST /{tid}/attributes/reorder ──

    async def test_reorder_bindings_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        tmpl = await create_attribute_template(admin_client)
        attr1 = await create_attribute(admin_client)
        attr2 = await create_attribute(admin_client)
        b1 = await bind_attribute_to_template(admin_client, tmpl["id"], attr1["id"])
        b2 = await bind_attribute_to_template(admin_client, tmpl["id"], attr2["id"])
        resp = await admin_client.post(
            f"/api/v1/catalog/attribute-templates/{tmpl['id']}/attributes/reorder",
            json={
                "items": [
                    {"bindingId": b2["id"], "sortOrder": 0},
                    {"bindingId": b1["id"], "sortOrder": 1},
                ]
            },
        )
        assert resp.status_code == 204


class TestAttributeTemplateSchemaFixes:
    """Tests for attribute template description_i18n optional fix."""

    async def test_create_template_without_description(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """POST /attribute-templates with minimal fields, NO descriptionI18n -> 201."""
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "code": f"tmpl_{suffix}",
            "nameI18n": {"ru": "Обувь", "en": "Footwear"},
        }
        resp = await admin_client.post(
            "/api/v1/catalog/attribute-templates", json=payload
        )
        assert resp.status_code == 201
