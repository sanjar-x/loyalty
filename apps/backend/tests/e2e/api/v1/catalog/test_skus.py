"""
E2E contract tests for SKU admin endpoints.

Validates HTTP status codes, camelCase response shapes, and error handling
for all SKU CRUD and matrix generation endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import (
    create_attribute,
    create_attribute_value,
    create_brand,
    create_category,
)

pytestmark = pytest.mark.asyncio


async def _create_product_with_variant(client: AsyncClient) -> dict:
    """Helper: create brand + category + product, return {product_id, variant_id}."""
    brand = await create_brand(client)
    cat = await create_category(client)
    resp = await client.post(
        "/api/v1/catalog/products",
        json={
            "titleI18N": {"ru": "SKU тест", "en": "SKU test"},
            "slug": f"sku-prod-{uuid.uuid4().hex[:8]}",
            "brandId": str(brand["id"]),
            "primaryCategoryId": str(cat["id"]),
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {"product_id": data["id"], "variant_id": data["defaultVariantId"]}


class TestSKUEndpoints:
    """Tests for /api/v1/catalog/products/{pid}/variants/{vid}/skus endpoints."""

    # ── POST .../skus ──

    async def test_add_sku_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        pv = await _create_product_with_variant(admin_client)
        resp = await admin_client.post(
            f"/api/v1/catalog/products/{pv['product_id']}/variants/{pv['variant_id']}/skus",
            json={
                "skuCode": f"SKU-{uuid.uuid4().hex[:6]}",
                "priceAmount": 10000,
                "priceCurrency": "RUB",
                "isActive": True,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "message" in data

    async def test_add_sku_duplicate_code_returns_409(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        pv = await _create_product_with_variant(admin_client)
        sku_code = f"DUP-{uuid.uuid4().hex[:6]}"
        url = f"/api/v1/catalog/products/{pv['product_id']}/variants/{pv['variant_id']}/skus"
        await admin_client.post(
            url,
            json={"skuCode": sku_code, "priceAmount": 1000, "priceCurrency": "RUB"},
        )
        resp = await admin_client.post(
            url,
            json={"skuCode": sku_code, "priceAmount": 2000, "priceCurrency": "RUB"},
        )
        assert resp.status_code == 409

    # ── GET .../skus ──

    async def test_list_skus_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        pv = await _create_product_with_variant(admin_client)
        # Add a SKU first
        await admin_client.post(
            f"/api/v1/catalog/products/{pv['product_id']}/variants/{pv['variant_id']}/skus",
            json={
                "skuCode": f"LST-{uuid.uuid4().hex[:6]}",
                "priceAmount": 5000,
                "priceCurrency": "RUB",
            },
        )
        resp = await admin_client.get(
            f"/api/v1/catalog/products/{pv['product_id']}/variants/{pv['variant_id']}/skus",
            params={"offset": 0, "limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1
        item = data["items"][0]
        for field in (
            "id",
            "productId",
            "variantId",
            "skuCode",
            "price",
            "isActive",
            "version",
            "createdAt",
            "updatedAt",
            "variantAttributes",
        ):
            assert field in item, f"Missing camelCase field: {field}"

    # ── PATCH .../skus/{sid} ──

    async def test_update_sku_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        pv = await _create_product_with_variant(admin_client)
        add_resp = await admin_client.post(
            f"/api/v1/catalog/products/{pv['product_id']}/variants/{pv['variant_id']}/skus",
            json={
                "skuCode": f"UPD-{uuid.uuid4().hex[:6]}",
                "priceAmount": 3000,
                "priceCurrency": "RUB",
            },
        )
        sku_id = add_resp.json()["id"]
        resp = await admin_client.patch(
            f"/api/v1/catalog/products/{pv['product_id']}/variants/{pv['variant_id']}/skus/{sku_id}",
            json={"priceAmount": 4000},
        )
        assert resp.status_code == 200

    # ── DELETE .../skus/{sid} ──

    async def test_delete_sku_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        pv = await _create_product_with_variant(admin_client)
        add_resp = await admin_client.post(
            f"/api/v1/catalog/products/{pv['product_id']}/variants/{pv['variant_id']}/skus",
            json={
                "skuCode": f"DEL-{uuid.uuid4().hex[:6]}",
                "priceAmount": 1000,
                "priceCurrency": "RUB",
            },
        )
        sku_id = add_resp.json()["id"]
        resp = await admin_client.delete(
            f"/api/v1/catalog/products/{pv['product_id']}/variants/{pv['variant_id']}/skus/{sku_id}"
        )
        assert resp.status_code == 204

    # ── POST .../skus/generate ──

    async def test_generate_sku_matrix_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        # Create variant-level dictionary attribute with 2 values
        attr = await create_attribute(admin_client, level="variant", is_dictionary=True)
        v1 = await create_attribute_value(
            admin_client,
            attr["id"],
            code=f"r_{uuid.uuid4().hex[:6]}",
            slug=f"r-{uuid.uuid4().hex[:6]}",
            value_i18n={"ru": "Красный", "en": "Red"},
        )
        v2 = await create_attribute_value(
            admin_client,
            attr["id"],
            code=f"b_{uuid.uuid4().hex[:6]}",
            slug=f"b-{uuid.uuid4().hex[:6]}",
            value_i18n={"ru": "Синий", "en": "Blue"},
        )

        pv = await _create_product_with_variant(admin_client)
        resp = await admin_client.post(
            f"/api/v1/catalog/products/{pv['product_id']}/variants/{pv['variant_id']}/skus/generate",
            json={
                "attributeSelections": [
                    {
                        "attributeId": attr["id"],
                        "valueIds": [v1["id"], v2["id"]],
                    }
                ],
                "priceAmount": 5000,
                "priceCurrency": "RUB",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "createdCount" in data
        assert "skippedCount" in data
        assert "skuIds" in data
        assert data["createdCount"] >= 1
