"""
E2E full product lifecycle test (API-04).

Proves the entire catalog API stack works end-to-end through the HTTP layer
by executing the complete product creation flow:
create brand -> category -> template -> bindings -> product -> variant ->
SKU -> media -> status transitions -> published.
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


async def test_full_product_lifecycle(
    admin_client: AsyncClient, db_session: AsyncSession
):
    """Full product lifecycle: create -> enrich -> review -> publish.

    This test proves the entire catalog API stack works end-to-end through
    the HTTP layer by executing the complete product creation flow documented
    in docs/api/product-creation-flow.md.
    """
    # Step 1: Create prerequisites
    brand = await create_brand(admin_client)
    template = await create_attribute_template(admin_client)
    attr = await create_attribute(
        admin_client,
        level="variant",
        is_dictionary=True,
        is_filterable=True,
    )
    val1 = await create_attribute_value(
        admin_client,
        attr["id"],
        code=f"red_{uuid.uuid4().hex[:6]}",
        slug=f"red-{uuid.uuid4().hex[:6]}",
        value_i18n={"ru": "Красный", "en": "Red"},
    )
    val2 = await create_attribute_value(
        admin_client,
        attr["id"],
        code=f"blue_{uuid.uuid4().hex[:6]}",
        slug=f"blue-{uuid.uuid4().hex[:6]}",
        value_i18n={"ru": "Синий", "en": "Blue"},
    )
    await bind_attribute_to_template(admin_client, template["id"], attr["id"])
    category = await create_category(admin_client, template_id=template["id"])

    # Step 2: Create product (DRAFT status)
    product_resp = await admin_client.post(
        "/api/v1/catalog/products",
        json={
            "titleI18N": {"ru": "Тестовый товар", "en": "Test Product"},
            "slug": f"lifecycle-{uuid.uuid4().hex[:8]}",
            "brandId": str(brand["id"]),
            "primaryCategoryId": str(category["id"]),
        },
    )
    assert product_resp.status_code == 201
    product = product_resp.json()
    product_id = product["id"]
    variant_id = product["defaultVariantId"]

    # Step 3: Add SKU with price
    sku_resp = await admin_client.post(
        f"/api/v1/catalog/products/{product_id}/variants/{variant_id}/skus",
        json={
            "skuCode": f"LIFE-{uuid.uuid4().hex[:6]}",
            "priceAmount": 9990,
            "priceCurrency": "RUB",
            "isActive": True,
            "variantAttributes": [
                {
                    "attributeId": str(attr["id"]),
                    "attributeValueId": str(val1["id"]),
                }
            ],
        },
    )
    assert sku_resp.status_code == 201

    # Step 4: Add external media asset (bypasses ImageBackend)
    media_resp = await admin_client.post(
        f"/api/v1/catalog/products/{product_id}/media",
        json={
            "isExternal": True,
            "url": "https://example.com/lifecycle-photo.jpg",
            "mediaType": "image",
            "role": "main",
            "sortOrder": 0,
        },
    )
    assert media_resp.status_code == 201

    # Step 5: Transition through FSM states
    # DRAFT -> ENRICHING
    resp = await admin_client.patch(
        f"/api/v1/catalog/products/{product_id}/status",
        json={"status": "enriching"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "enriching"

    # ENRICHING -> READY_FOR_REVIEW
    resp = await admin_client.patch(
        f"/api/v1/catalog/products/{product_id}/status",
        json={"status": "ready_for_review"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready_for_review"

    # READY_FOR_REVIEW -> PUBLISHED
    resp = await admin_client.patch(
        f"/api/v1/catalog/products/{product_id}/status",
        json={"status": "published"},
    )
    assert resp.status_code == 200
    product_data = resp.json()
    assert product_data["status"] == "published"
    assert product_data["publishedAt"] is not None

    # Step 6: Verify product detail has all nested data
    detail_resp = await admin_client.get(f"/api/v1/catalog/products/{product_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "published"
    assert len(detail["variants"]) >= 1
    assert any(len(v["skus"]) > 0 for v in detail["variants"])

    # Step 7: Verify product appears in list
    list_resp = await admin_client.get(
        "/api/v1/catalog/products", params={"status": "published"}
    )
    assert list_resp.status_code == 200
    published_ids = [p["id"] for p in list_resp.json()["items"]]
    assert product_id in published_ids
