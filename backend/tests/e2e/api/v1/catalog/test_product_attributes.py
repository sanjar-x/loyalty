"""
E2E contract tests for Product Attribute assignment endpoints.

Validates HTTP status codes, camelCase response shapes, and error handling
for all product attribute assignment CRUD endpoints.
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
    create_brand,
    create_category,
)

pytestmark = pytest.mark.asyncio


async def _setup_product_with_attribute(
    client: AsyncClient,
) -> dict:
    """Create the full prerequisite chain for product attribute assignment.

    Returns dict with: product_id, attribute_id, attribute_value_id, template_id.
    """
    # 1. Create attribute template
    template = await create_attribute_template(client)
    # 2. Create attribute (product-level, dictionary)
    attr = await create_attribute(client, level="product", is_dictionary=True)
    # 3. Bind attribute to template
    await bind_attribute_to_template(
        client, template["id"], attr["id"], requirement_level="optional"
    )
    # 4. Create category with template
    cat = await create_category(client, template_id=template["id"])
    # 5. Create brand
    brand = await create_brand(client)
    # 6. Create product
    resp = await client.post(
        "/api/v1/catalog/products",
        json={
            "titleI18n": {"ru": "Атрибут тест", "en": "Attr test"},
            "slug": f"attr-prod-{uuid.uuid4().hex[:8]}",
            "brandId": str(brand["id"]),
            "primaryCategoryId": str(cat["id"]),
        },
    )
    assert resp.status_code == 201, resp.text
    product = resp.json()
    # 7. Create attribute value
    val = await create_attribute_value(client, attr["id"])
    return {
        "product_id": product["id"],
        "attribute_id": attr["id"],
        "attribute_value_id": val["id"],
        "template_id": template["id"],
    }


class TestProductAttributeEndpoints:
    """Tests for /api/v1/catalog/products/{pid}/attributes endpoints."""

    # ── POST /products/{pid}/attributes ──

    async def test_assign_product_attribute_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _setup_product_with_attribute(admin_client)
        resp = await admin_client.post(
            f"/api/v1/catalog/products/{setup['product_id']}/attributes",
            json={
                "attributeId": setup["attribute_id"],
                "attributeValueId": setup["attribute_value_id"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "message" in data

    async def test_assign_duplicate_attribute_returns_409(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _setup_product_with_attribute(admin_client)
        url = f"/api/v1/catalog/products/{setup['product_id']}/attributes"
        payload = {
            "attributeId": setup["attribute_id"],
            "attributeValueId": setup["attribute_value_id"],
        }
        await admin_client.post(url, json=payload)
        resp = await admin_client.post(url, json=payload)
        assert resp.status_code == 409

    # ── GET /products/{pid}/attributes ──

    async def test_list_product_attributes_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _setup_product_with_attribute(admin_client)
        await admin_client.post(
            f"/api/v1/catalog/products/{setup['product_id']}/attributes",
            json={
                "attributeId": setup["attribute_id"],
                "attributeValueId": setup["attribute_value_id"],
            },
        )
        resp = await admin_client.get(
            f"/api/v1/catalog/products/{setup['product_id']}/attributes",
            params={"offset": 0, "limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    # ── POST /products/{pid}/attributes/bulk ──

    async def test_bulk_assign_product_attributes_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _setup_product_with_attribute(admin_client)
        resp = await admin_client.post(
            f"/api/v1/catalog/products/{setup['product_id']}/attributes/bulk",
            json={
                "items": [
                    {
                        "attributeId": setup["attribute_id"],
                        "attributeValueId": setup["attribute_value_id"],
                    }
                ]
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "assignedCount" in data
        assert "pavIds" in data

    # ── DELETE /products/{pid}/attributes/{attribute_id} ──

    async def test_delete_product_attribute_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _setup_product_with_attribute(admin_client)
        await admin_client.post(
            f"/api/v1/catalog/products/{setup['product_id']}/attributes",
            json={
                "attributeId": setup["attribute_id"],
                "attributeValueId": setup["attribute_value_id"],
            },
        )
        resp = await admin_client.delete(
            f"/api/v1/catalog/products/{setup['product_id']}/attributes/{setup['attribute_id']}"
        )
        assert resp.status_code == 204
