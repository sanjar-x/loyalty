"""
E2E contract tests for Storefront Product endpoints (PLP + PDP).

Tests the public endpoints:
    GET /api/v1/catalog/storefront/products           — PLP listing
    GET /api/v1/catalog/storefront/products/{slug}    — PDP detail

Product lifecycle: DRAFT → ENRICHING → READY_FOR_REVIEW → PUBLISHED.
To reach PUBLISHED, the product needs at least one active SKU with a price.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import create_brand, create_category

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/catalog"
PLP = f"{BASE}/storefront/products"
PDP = f"{BASE}/storefront/products"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _ensure_currency(db_session: AsyncSession) -> None:
    """Ensure the RUB currency row exists (SKU.currency FK requires it)."""
    await db_session.execute(
        text(
            "INSERT INTO currencies (code, numeric, name, minor_unit, is_active)"
            " VALUES ('RUB', '643', 'Russian Ruble', 2, true)"
            " ON CONFLICT (code) DO NOTHING"
        )
    )
    await db_session.flush()


# ---------------------------------------------------------------------------
# Helpers — create a published product via admin API
# ---------------------------------------------------------------------------


async def _create_published_product(
    admin_client: AsyncClient,
    *,
    category_id: str,
    brand_id: str,
    slug: str | None = None,
    title_i18n: dict | None = None,
) -> dict:
    """Create a published product with a default variant and active SKU."""
    slug = slug or f"product-{uuid.uuid4().hex[:8]}"
    title_i18n = title_i18n or {"ru": "Тестовый товар", "en": "Test Product"}

    # 1. Create product (DRAFT)
    resp = await admin_client.post(
        f"{BASE}/products",
        json={
            "titleI18N": title_i18n,
            "slug": slug,
            "brandId": brand_id,
            "primaryCategoryId": category_id,
        },
    )
    assert resp.status_code == 201, f"create product failed: {resp.text}"
    product = resp.json()
    product_id = product["id"]
    variant_id = product["defaultVariantId"]

    # 2. Add a SKU with price (nested under variant)
    resp = await admin_client.post(
        f"{BASE}/products/{product_id}/variants/{variant_id}/skus",
        json={
            "skuCode": f"SKU-{uuid.uuid4().hex[:6]}",
            "priceAmount": 1500_00,
            "priceCurrency": "RUB",
            "isActive": True,
        },
    )
    assert resp.status_code == 201, f"add SKU failed: {resp.text}"

    # 3. Add external media asset (required for publishing)
    resp = await admin_client.post(
        f"{BASE}/products/{product_id}/media",
        json={
            "isExternal": True,
            "url": "https://example.com/test-product.jpg",
            "mediaType": "image",
            "role": "main",
            "sortOrder": 0,
        },
    )
    assert resp.status_code == 201, f"add media failed: {resp.text}"

    # 4. Transition DRAFT → ENRICHING → READY_FOR_REVIEW → PUBLISHED
    for new_status in ("enriching", "ready_for_review", "published"):
        resp = await admin_client.patch(
            f"{BASE}/products/{product_id}/status",
            json={"status": new_status},
        )
        assert resp.status_code == 200, (
            f"status → {new_status} failed: {resp.status_code} {resp.text}"
        )

    return {
        "id": product_id,
        "slug": slug,
        "variant_id": variant_id,
        "category_id": category_id,
        "brand_id": brand_id,
    }


# ---------------------------------------------------------------------------
# PLP Tests
# ---------------------------------------------------------------------------


class TestStorefrontPLP:
    """Tests for GET /api/v1/catalog/storefront/products (PLP listing)."""

    async def test_plp_returns_products_for_category(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Published products in a category appear in PLP listing."""
        brand = await create_brand(admin_client)
        category = await create_category(admin_client)
        product = await _create_published_product(
            admin_client,
            category_id=category["id"],
            brand_id=brand["id"],
        )

        resp = await async_client.get(PLP, params={"category_id": category["id"]})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "hasNext" in data
        slugs = [item["slug"] for item in data["items"]]
        assert product["slug"] in slugs

    async def test_plp_empty_category(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """An empty category returns an empty items list."""
        category = await create_category(admin_client)
        resp = await async_client.get(PLP, params={"category_id": category["id"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["hasNext"] is False

    async def test_plp_requires_category_id(
        self,
        async_client: AsyncClient,
    ):
        """Missing category_id query param returns 422."""
        resp = await async_client.get(PLP)
        assert resp.status_code == 422

    async def test_plp_has_cache_control_header(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """PLP response includes Cache-Control header."""
        category = await create_category(admin_client)
        resp = await async_client.get(PLP, params={"category_id": category["id"]})
        assert resp.status_code == 200
        assert "cache-control" in resp.headers

    async def test_plp_card_response_shape(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Each card in PLP has expected fields."""
        brand = await create_brand(admin_client)
        category = await create_category(admin_client)
        await _create_published_product(
            admin_client,
            category_id=category["id"],
            brand_id=brand["id"],
        )

        resp = await async_client.get(PLP, params={"category_id": category["id"]})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        card = items[0]
        for field in ("id", "slug", "titleI18N", "inStock", "variantCount"):
            assert field in card, f"Missing field: {field}"

    async def test_plp_i18n_projection(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """With ?lang=ru, title field is projected from titleI18N."""
        brand = await create_brand(admin_client)
        category = await create_category(admin_client)
        await _create_published_product(
            admin_client,
            category_id=category["id"],
            brand_id=brand["id"],
            title_i18n={"ru": "Кроссовки", "en": "Sneakers"},
        )

        resp = await async_client.get(
            PLP, params={"category_id": category["id"], "lang": "ru"}
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        assert items[0]["title"] == "Кроссовки"

    async def test_plp_pagination_limit(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Respects limit param and returns correct number of items."""
        brand = await create_brand(admin_client)
        category = await create_category(admin_client)
        # Create 3 products
        for _i in range(3):
            await _create_published_product(
                admin_client,
                category_id=category["id"],
                brand_id=brand["id"],
            )

        resp = await async_client.get(
            PLP, params={"category_id": category["id"], "limit": 2}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["hasNext"] is True
        assert data["nextCursor"] is not None

    async def test_plp_cursor_pagination_no_duplicates(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Cursor pagination returns no duplicate products across pages."""
        brand = await create_brand(admin_client)
        category = await create_category(admin_client)
        for _ in range(4):
            await _create_published_product(
                admin_client,
                category_id=category["id"],
                brand_id=brand["id"],
            )

        # Page 1
        resp1 = await async_client.get(
            PLP, params={"category_id": category["id"], "limit": 2}
        )
        assert resp1.status_code == 200, f"PLP page 1: {resp1.status_code} {resp1.text}"
        data1 = resp1.json()
        ids_page1 = {item["id"] for item in data1["items"]}

        # Page 2
        resp2 = await async_client.get(
            PLP,
            params={
                "category_id": category["id"],
                "limit": 2,
                "cursor": data1["nextCursor"],
            },
        )
        data2 = resp2.json()
        ids_page2 = {item["id"] for item in data2["items"]}

        # No overlap
        assert ids_page1.isdisjoint(ids_page2)

    async def test_plp_sort_invalid_value(
        self,
        async_client: AsyncClient,
    ):
        """Invalid sort value returns 422."""
        resp = await async_client.get(
            PLP,
            params={"category_id": str(uuid.uuid4()), "sort": "invalid_sort"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PDP Tests
# ---------------------------------------------------------------------------


class TestStorefrontPDP:
    """Tests for GET /api/v1/catalog/storefront/products/{slug} (PDP detail)."""

    async def test_pdp_returns_product_detail(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Published product is returned by slug."""
        brand = await create_brand(admin_client)
        category = await create_category(admin_client)
        product = await _create_published_product(
            admin_client,
            category_id=category["id"],
            brand_id=brand["id"],
            slug="pdp-test-product",
        )

        resp = await async_client.get(f"{PDP}/{product['slug']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "pdp-test-product"
        assert "titleI18N" in data
        assert "variants" in data
        assert "breadcrumbs" in data
        assert "version" in data

    async def test_pdp_includes_price(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """PDP includes price from the cheapest SKU."""
        brand = await create_brand(admin_client)
        category = await create_category(admin_client)
        product = await _create_published_product(
            admin_client,
            category_id=category["id"],
            brand_id=brand["id"],
        )

        resp = await async_client.get(f"{PDP}/{product['slug']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["price"] is not None
        assert data["price"]["amount"] == 1500_00
        assert data["inStock"] is True

    async def test_pdp_not_found_for_unpublished(
        self,
        async_client: AsyncClient,
    ):
        """Non-existent slug returns 404."""
        resp = await async_client.get(f"{PDP}/nonexistent-slug-xyz")
        assert resp.status_code == 404

    async def test_pdp_has_etag_header(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """PDP response includes ETag header."""
        brand = await create_brand(admin_client)
        category = await create_category(admin_client)
        product = await _create_published_product(
            admin_client,
            category_id=category["id"],
            brand_id=brand["id"],
        )

        resp = await async_client.get(f"{PDP}/{product['slug']}")
        assert resp.status_code == 200
        assert "etag" in resp.headers

    async def test_pdp_has_cache_control_header(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """PDP response includes Cache-Control header."""
        brand = await create_brand(admin_client)
        category = await create_category(admin_client)
        product = await _create_published_product(
            admin_client,
            category_id=category["id"],
            brand_id=brand["id"],
        )

        resp = await async_client.get(f"{PDP}/{product['slug']}")
        assert resp.status_code == 200
        assert "cache-control" in resp.headers

    async def test_pdp_i18n_projection(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """With ?lang=en, title field is projected from titleI18N."""
        brand = await create_brand(admin_client)
        category = await create_category(admin_client)
        product = await _create_published_product(
            admin_client,
            category_id=category["id"],
            brand_id=brand["id"],
            title_i18n={"ru": "Ботинки", "en": "Boots"},
        )

        resp = await async_client.get(f"{PDP}/{product['slug']}", params={"lang": "en"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Boots"

    async def test_pdp_has_variants_and_media(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """PDP includes variants list (at least 1 from default variant)."""
        brand = await create_brand(admin_client)
        category = await create_category(admin_client)
        product = await _create_published_product(
            admin_client,
            category_id=category["id"],
            brand_id=brand["id"],
        )

        resp = await async_client.get(f"{PDP}/{product['slug']}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["variants"], list)
        assert len(data["variants"]) >= 1
        assert isinstance(data["media"], list)
