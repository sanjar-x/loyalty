"""
E2E contract tests for Storefront Search endpoints (Phase 3).

Tests the public endpoints:
    GET /api/v1/catalog/storefront/search          — Full-text product search
    GET /api/v1/catalog/storefront/search/suggest   — Autocomplete suggestions

Products are created via admin API and transitioned to PUBLISHED status.
Full-text search uses PostgreSQL tsvector/tsquery with the
``catalog_product_search_vector`` SQL function.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import create_brand, create_category

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/catalog"
SEARCH = f"{BASE}/storefront/search"
SUGGEST = f"{SEARCH}/suggest"


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
    description_i18n: dict | None = None,
    tags: list[str] | None = None,
    price: int = 1500_00,
) -> dict:
    """Create a published product with a default variant and active SKU."""
    slug = slug or f"product-{uuid.uuid4().hex[:8]}"
    title_i18n = title_i18n or {"ru": "Тестовый товар", "en": "Test Product"}

    payload: dict = {
        "titleI18N": title_i18n,
        "slug": slug,
        "brandId": brand_id,
        "primaryCategoryId": category_id,
    }
    if description_i18n is not None:
        payload["descriptionI18N"] = description_i18n
    if tags is not None:
        payload["tags"] = tags

    # 1. Create product (DRAFT)
    resp = await admin_client.post(f"{BASE}/products", json=payload)
    assert resp.status_code == 201, f"create product failed: {resp.text}"
    product = resp.json()
    product_id = product["id"]
    variant_id = product["defaultVariantId"]

    # 2. Add a SKU with price
    resp = await admin_client.post(
        f"{BASE}/products/{product_id}/variants/{variant_id}/skus",
        json={
            "skuCode": f"SKU-{uuid.uuid4().hex[:6]}",
            "priceAmount": price,
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
        "title_i18n": title_i18n,
    }


@pytest.fixture()
async def search_seed(admin_client: AsyncClient) -> dict:
    """Create a small catalog suitable for search tests.

    Products:
        - "Кроссовки Nike Air Max" (tags: [nike, airmax, кроссовки])
        - "Кроссовки Adidas Ultraboost" (tags: [adidas, ultraboost])
        - "Футболка Nike Dri-Fit" (tags: [nike, dri-fit, футболка])

    Categories: Обувь, Одежда
    Brands: Nike, Adidas
    """
    brand_nike = await create_brand(admin_client, name="Nike", slug="nike")
    brand_adidas = await create_brand(admin_client, name="Adidas", slug="adidas")

    cat_shoes = await create_category(
        admin_client,
        name_i18n={"ru": "Обувь", "en": "Shoes"},
        slug="shoes",
    )
    cat_clothing = await create_category(
        admin_client,
        name_i18n={"ru": "Одежда", "en": "Clothing"},
        slug="clothing",
    )

    p_airmax = await _create_published_product(
        admin_client,
        category_id=cat_shoes["id"],
        brand_id=brand_nike["id"],
        slug="krossovki-nike-air-max",
        title_i18n={"ru": "Кроссовки Nike Air Max", "en": "Nike Air Max Sneakers"},
        description_i18n={
            "ru": "Легкие беговые кроссовки",
            "en": "Lightweight running sneakers",
        },
        tags=["nike", "airmax", "кроссовки"],
        price=12000_00,
    )

    p_ultraboost = await _create_published_product(
        admin_client,
        category_id=cat_shoes["id"],
        brand_id=brand_adidas["id"],
        slug="krossovki-adidas-ultraboost",
        title_i18n={
            "ru": "Кроссовки Adidas Ultraboost",
            "en": "Adidas Ultraboost Sneakers",
        },
        tags=["adidas", "ultraboost"],
        price=15000_00,
    )

    p_shirt = await _create_published_product(
        admin_client,
        category_id=cat_clothing["id"],
        brand_id=brand_nike["id"],
        slug="futbolka-nike-dri-fit",
        title_i18n={"ru": "Футболка Nike Dri-Fit", "en": "Nike Dri-Fit T-Shirt"},
        tags=["nike", "dri-fit", "футболка"],
        price=3500_00,
    )

    return {
        "brands": {"nike": brand_nike, "adidas": brand_adidas},
        "categories": {"shoes": cat_shoes, "clothing": cat_clothing},
        "products": {
            "airmax": p_airmax,
            "ultraboost": p_ultraboost,
            "shirt": p_shirt,
        },
    }


# ===========================================================================
# Search endpoint tests
# ===========================================================================


class TestSearchProducts:
    """Tests for GET /api/v1/catalog/storefront/search."""

    async def test_search_by_russian_keyword(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Russian word 'Кроссовки' should match both shoe products."""
        resp = await async_client.get(SEARCH, params={"q": "Кроссовки"})
        assert resp.status_code == 200

        data = resp.json()
        assert "items" in data
        slugs = {item["slug"] for item in data["items"]}
        assert "krossovki-nike-air-max" in slugs
        assert "krossovki-adidas-ultraboost" in slugs
        # Shirt should NOT match.
        assert "futbolka-nike-dri-fit" not in slugs

    async def test_search_by_english_keyword(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """English word 'sneakers' should match shoe products."""
        resp = await async_client.get(SEARCH, params={"q": "sneakers"})
        assert resp.status_code == 200

        data = resp.json()
        slugs = {item["slug"] for item in data["items"]}
        assert "krossovki-nike-air-max" in slugs
        assert "krossovki-adidas-ultraboost" in slugs

    async def test_search_by_brand_name(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Search for 'Nike' should match Nike products (title contains it)."""
        resp = await async_client.get(SEARCH, params={"q": "Nike"})
        assert resp.status_code == 200

        data = resp.json()
        slugs = {item["slug"] for item in data["items"]}
        assert "krossovki-nike-air-max" in slugs
        assert "futbolka-nike-dri-fit" in slugs
        # Adidas product should NOT match
        assert "krossovki-adidas-ultraboost" not in slugs

    async def test_search_prefix_matching(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Partial word should match via prefix (last token gets :*)."""
        resp = await async_client.get(SEARCH, params={"q": "Кросс"})
        assert resp.status_code == 200

        data = resp.json()
        assert len(data["items"]) >= 1
        # At least one shoe product should match
        slugs = {item["slug"] for item in data["items"]}
        assert slugs & {"krossovki-nike-air-max", "krossovki-adidas-ultraboost"}

    async def test_search_with_category_filter(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Searching Nike + category=shoes should exclude the shirt."""
        cat_shoes_id = search_seed["categories"]["shoes"]["id"]
        resp = await async_client.get(
            SEARCH, params={"q": "Nike", "category_id": cat_shoes_id}
        )
        assert resp.status_code == 200

        data = resp.json()
        slugs = {item["slug"] for item in data["items"]}
        assert "krossovki-nike-air-max" in slugs
        assert "futbolka-nike-dri-fit" not in slugs

    async def test_search_with_brand_filter(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Search 'Кроссовки' + brand=Adidas → only Ultraboost."""
        adidas_id = search_seed["brands"]["adidas"]["id"]
        resp = await async_client.get(
            SEARCH, params={"q": "Кроссовки", "brand_id": adidas_id}
        )
        assert resp.status_code == 200

        data = resp.json()
        slugs = {item["slug"] for item in data["items"]}
        assert "krossovki-adidas-ultraboost" in slugs
        assert "krossovki-nike-air-max" not in slugs

    async def test_search_with_price_filter(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Search with price_max should filter expensive products."""
        resp = await async_client.get(
            SEARCH, params={"q": "Кроссовки", "price_max": 13000_00}
        )
        assert resp.status_code == 200

        data = resp.json()
        slugs = {item["slug"] for item in data["items"]}
        # Air Max (12000_00) should be in, Ultraboost (15000_00) should be out
        assert "krossovki-nike-air-max" in slugs
        assert "krossovki-adidas-ultraboost" not in slugs

    async def test_search_no_results(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Search for a nonsense string should return empty results."""
        resp = await async_client.get(SEARCH, params={"q": "xyznonexistent12345"})
        assert resp.status_code == 200

        data = resp.json()
        assert data["items"] == []
        assert data["hasNext"] is False

    async def test_search_returns_card_shape(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Verify response items have the expected product card shape."""
        resp = await async_client.get(SEARCH, params={"q": "Nike Air Max"})
        assert resp.status_code == 200

        data = resp.json()
        assert len(data["items"]) >= 1
        card = data["items"][0]
        assert "slug" in card
        assert "titleI18N" in card
        assert "price" in card
        assert "brand" in card

    async def test_search_pagination(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Search with limit=1 should paginate correctly."""
        resp = await async_client.get(SEARCH, params={"q": "Кроссовки", "limit": 1})
        assert resp.status_code == 200

        data = resp.json()
        assert len(data["items"]) == 1
        assert data["hasNext"] is True
        assert data["nextCursor"] is not None

        # Follow the cursor
        resp2 = await async_client.get(
            SEARCH,
            params={"q": "Кроссовки", "limit": 1, "cursor": data["nextCursor"]},
        )
        assert resp2.status_code == 200

        data2 = resp2.json()
        assert len(data2["items"]) == 1
        # Different product than page 1
        assert data2["items"][0]["slug"] != data["items"][0]["slug"]

    async def test_search_include_total(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """include_total=true should return a total count."""
        resp = await async_client.get(
            SEARCH, params={"q": "Кроссовки", "include_total": True}
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 2

    async def test_search_with_facets_requires_category_id(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """include_facets=true without category_id should still return results
        but facets should be null (no error)."""
        resp = await async_client.get(
            SEARCH, params={"q": "Nike", "include_facets": True}
        )
        assert resp.status_code == 200
        data = resp.json()
        # Facets should be null/absent since no category_id provided.
        assert data.get("facets") is None

    async def test_search_with_facets_and_category(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """include_facets=true with category_id should include facet data."""
        cat_shoes_id = search_seed["categories"]["shoes"]["id"]
        resp = await async_client.get(
            SEARCH,
            params={
                "q": "Кроссовки",
                "category_id": cat_shoes_id,
                "include_facets": True,
            },
        )
        assert resp.status_code == 200

        data = resp.json()
        assert len(data["items"]) >= 1
        # Facets should be present (even if minimal)
        assert data["facets"] is not None

    async def test_search_sort_by_price_asc(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Sort by price_asc should return cheaper products first."""
        resp = await async_client.get(
            SEARCH, params={"q": "Кроссовки", "sort": "price_asc"}
        )
        assert resp.status_code == 200

        data = resp.json()
        items = data["items"]
        assert len(items) == 2
        # Air Max (12000_00) should be before Ultraboost (15000_00)
        assert items[0]["slug"] == "krossovki-nike-air-max"
        assert items[1]["slug"] == "krossovki-adidas-ultraboost"

    async def test_search_sort_by_price_desc(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Sort by price_desc should return expensive products first."""
        resp = await async_client.get(
            SEARCH, params={"q": "Кроссовки", "sort": "price_desc"}
        )
        assert resp.status_code == 200

        data = resp.json()
        items = data["items"]
        assert len(items) == 2
        # Ultraboost (15000_00) should be first
        assert items[0]["slug"] == "krossovki-adidas-ultraboost"
        assert items[1]["slug"] == "krossovki-nike-air-max"

    async def test_search_q_missing_returns_422(self, async_client: AsyncClient):
        """Missing q param should return 422."""
        resp = await async_client.get(SEARCH)
        assert resp.status_code == 422

    async def test_search_q_empty_returns_422(self, async_client: AsyncClient):
        """Empty q param should return 422 (min_length=1)."""
        resp = await async_client.get(SEARCH, params={"q": ""})
        assert resp.status_code == 422

    async def test_search_cache_control_header(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Response should include Cache-Control header."""
        resp = await async_client.get(SEARCH, params={"q": "Nike"})
        assert resp.status_code == 200
        assert "cache-control" in resp.headers


# ===========================================================================
# Suggest endpoint tests
# ===========================================================================


class TestSearchSuggest:
    """Tests for GET /api/v1/catalog/storefront/search/suggest."""

    async def test_suggest_returns_products(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Prefix 'кросс' should suggest shoe products."""
        resp = await async_client.get(SUGGEST, params={"q": "кросс"})
        assert resp.status_code == 200

        data = resp.json()
        assert isinstance(data, list)
        product_suggestions = [s for s in data if s["type"] == "product"]
        assert len(product_suggestions) >= 1

    async def test_suggest_returns_categories(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Prefix 'обу' should suggest the 'Обувь' category."""
        resp = await async_client.get(SUGGEST, params={"q": "обу"})
        assert resp.status_code == 200

        data = resp.json()
        category_suggestions = [s for s in data if s["type"] == "category"]
        assert len(category_suggestions) >= 1
        assert any(s["slug"] == "shoes" for s in category_suggestions)

    async def test_suggest_returns_brands(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Prefix 'ni' should suggest the 'Nike' brand."""
        resp = await async_client.get(SUGGEST, params={"q": "ni"})
        assert resp.status_code == 200

        data = resp.json()
        brand_suggestions = [s for s in data if s["type"] == "brand"]
        assert len(brand_suggestions) >= 1
        assert any(s["slug"] == "nike" for s in brand_suggestions)

    async def test_suggest_mixed_types(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Prefix 'nike' should suggest brand + products in mixed response."""
        resp = await async_client.get(SUGGEST, params={"q": "nike"})
        assert resp.status_code == 200

        data = resp.json()
        types = {s["type"] for s in data}
        # Should have at least brand and product
        assert "brand" in types
        # Products that contain "nike" in title should also appear
        assert "product" in types

    async def test_suggest_respects_limit(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Limit parameter should cap the number of results."""
        resp = await async_client.get(SUGGEST, params={"q": "nike", "limit": 2})
        assert resp.status_code == 200

        data = resp.json()
        assert len(data) <= 2

    async def test_suggest_min_query_length(self, async_client: AsyncClient):
        """Single character should return 422 (min_length=2)."""
        resp = await async_client.get(SUGGEST, params={"q": "a"})
        assert resp.status_code == 422

    async def test_suggest_no_results(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Nonexistent prefix should return empty list."""
        resp = await async_client.get(SUGGEST, params={"q": "zzznonexistent"})
        assert resp.status_code == 200

        data = resp.json()
        assert data == []

    async def test_suggest_special_characters(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Special characters in query should not cause errors."""
        resp = await async_client.get(SUGGEST, params={"q": "nike%"})
        assert resp.status_code == 200
        # Should not crash — may return results or empty
        assert isinstance(resp.json(), list)

    async def test_suggest_response_shape(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Each suggestion should have type, text, slug fields."""
        resp = await async_client.get(SUGGEST, params={"q": "nike"})
        assert resp.status_code == 200

        data = resp.json()
        assert len(data) >= 1
        for item in data:
            assert "type" in item
            assert "text" in item
            assert "slug" in item
            assert item["type"] in ("product", "category", "brand")

    async def test_suggest_with_lang_param(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Suggest with lang=en should still work."""
        resp = await async_client.get(SUGGEST, params={"q": "nike", "lang": "en"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_suggest_cache_control(
        self, async_client: AsyncClient, search_seed: dict
    ):
        """Response should include Cache-Control header."""
        resp = await async_client.get(SUGGEST, params={"q": "nike"})
        assert resp.status_code == 200
        assert "cache-control" in resp.headers
