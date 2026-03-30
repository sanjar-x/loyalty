"""
E2E contract tests for Storefront category-attribute endpoints (API-02).

Public storefront endpoints (filters, card-attributes, comparison-attributes) do NOT
require authentication. Only form-attributes requires catalog:manage permission.

Validates response shapes and correct attribute projection for categories with
and without attribute templates.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import (
    bind_attribute_to_template,
    create_attribute,
    create_attribute_template,
    create_attribute_value,
    create_category,
)

pytestmark = pytest.mark.asyncio


async def _setup_category_with_template(client: AsyncClient) -> dict:
    """Create a category with a template bound to a filterable, visible, comparable attribute.

    Returns dict with: category_id, template_id, attribute_id.
    """
    template = await create_attribute_template(client)
    attr = await create_attribute(
        client,
        is_filterable=True,
        is_visible_on_card=True,
        is_comparable=True,
        is_dictionary=True,
    )
    await create_attribute_value(client, attr["id"])
    await bind_attribute_to_template(
        client, template["id"], attr["id"], requirement_level="required"
    )
    cat = await create_category(client, template_id=template["id"])
    return {
        "category_id": cat["id"],
        "template_id": template["id"],
        "attribute_id": attr["id"],
    }


class TestStorefrontEndpoints:
    """Tests for /api/v1/catalog/storefront/categories/{cid}/ endpoints."""

    # ── GET .../filters ──

    async def test_get_filterable_attributes_success(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        setup = await _setup_category_with_template(admin_client)
        # Public endpoint -- use async_client (no auth)
        resp = await async_client.get(
            f"/api/v1/catalog/storefront/categories/{setup['category_id']}/filters"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "categoryId" in data
        assert "attributes" in data
        assert isinstance(data["attributes"], list)
        if len(data["attributes"]) > 0:
            attr = data["attributes"][0]
            for field in (
                "attributeId",
                "code",
                "slug",
                "nameI18n",
                "dataType",
                "uiType",
                "isDictionary",
                "selectionMode",
                "values",
                "sortOrder",
            ):
                assert field in attr, f"Missing camelCase field: {field}"

    async def test_get_filterable_attributes_with_lang_projection(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        setup = await _setup_category_with_template(admin_client)
        resp = await async_client.get(
            f"/api/v1/catalog/storefront/categories/{setup['category_id']}/filters",
            params={"lang": "ru"},
        )
        assert resp.status_code == 200
        data = resp.json()
        if len(data["attributes"]) > 0:
            attr = data["attributes"][0]
            assert "name" in attr  # Projected name field present

    async def test_storefront_filters_no_template_returns_empty(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        # Category without template -> empty attributes
        cat = await create_category(admin_client)
        resp = await async_client.get(
            f"/api/v1/catalog/storefront/categories/{cat['id']}/filters"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["attributes"] == []

    # ── GET .../card-attributes ──

    async def test_get_card_attributes_success(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        setup = await _setup_category_with_template(admin_client)
        resp = await async_client.get(
            f"/api/v1/catalog/storefront/categories/{setup['category_id']}/card-attributes"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "categoryId" in data
        assert "groups" in data

    # ── GET .../comparison-attributes ──

    async def test_get_comparison_attributes_success(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        setup = await _setup_category_with_template(admin_client)
        resp = await async_client.get(
            f"/api/v1/catalog/storefront/categories/{setup['category_id']}/comparison-attributes"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "categoryId" in data
        assert "attributes" in data

    # ── GET .../form-attributes (requires catalog:manage) ──

    async def test_get_form_attributes_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _setup_category_with_template(admin_client)
        resp = await admin_client.get(
            f"/api/v1/catalog/storefront/categories/{setup['category_id']}/form-attributes"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "categoryId" in data
        assert "groups" in data

    async def test_storefront_form_attributes_requires_auth(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        setup = await _setup_category_with_template(admin_client)
        # Anonymous request to form-attributes -> 401
        resp = await async_client.get(
            f"/api/v1/catalog/storefront/categories/{setup['category_id']}/form-attributes"
        )
        assert resp.status_code == 401
