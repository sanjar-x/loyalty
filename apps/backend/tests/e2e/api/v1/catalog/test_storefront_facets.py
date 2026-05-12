"""
E2E tests for Phase 2 — Faceted Filtering on Storefront PLP.

Tests the EAV attribute filter (attr.* query params) and facet count
computation (include_facets=true) on the PLP endpoint:
    GET /api/v1/catalog/storefront/products

Setup: creates a template with two filterable attributes (color, material),
binds them, creates a category with that template, publishes products
with different attribute values, and tests filtering + facet counts.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
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

BASE = "/api/v1/catalog"
PLP = f"{BASE}/storefront/products"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _ensure_currency(db_session: AsyncSession) -> None:
    """Ensure the RUB currency row exists."""
    await db_session.execute(
        text(
            "INSERT INTO currencies (code, numeric, name, minor_unit, is_active)"
            " VALUES ('RUB', '643', 'Russian Ruble', 2, true)"
            " ON CONFLICT (code) DO NOTHING"
        )
    )
    await db_session.flush()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_published_product(
    admin_client: AsyncClient,
    *,
    category_id: str,
    brand_id: str,
    slug: str | None = None,
    price: int = 1500_00,
    attribute_assignments: list[tuple[str, str]] | None = None,
) -> dict:
    """Create a published product optionally with attribute assignments.

    ``attribute_assignments`` is a list of ``(attribute_id, attribute_value_id)``
    tuples to assign after creation.
    """
    slug = slug or f"product-{uuid.uuid4().hex[:8]}"

    # 1. Create product (DRAFT)
    resp = await admin_client.post(
        f"{BASE}/products",
        json={
            "titleI18N": {"ru": "Товар", "en": "Product"},
            "slug": slug,
            "brandId": brand_id,
            "primaryCategoryId": category_id,
        },
    )
    assert resp.status_code == 201, f"create product failed: {resp.text}"
    product = resp.json()
    product_id = product["id"]
    variant_id = product["defaultVariantId"]

    # 2. Add SKU with price
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

    # 3. Add external media (required for publish)
    resp = await admin_client.post(
        f"{BASE}/products/{product_id}/media",
        json={
            "isExternal": True,
            "url": "https://example.com/img.jpg",
            "mediaType": "image",
            "role": "main",
            "sortOrder": 0,
        },
    )
    assert resp.status_code == 201, f"add media failed: {resp.text}"

    # 4. Assign attributes (before publish)
    for attr_id, val_id in attribute_assignments or []:
        resp = await admin_client.post(
            f"{BASE}/products/{product_id}/attributes",
            json={"attributeId": attr_id, "attributeValueId": val_id},
        )
        assert resp.status_code == 201, (
            f"assign attr failed: {resp.status_code} {resp.text}"
        )

    # 5. Publish: DRAFT → ENRICHING → READY_FOR_REVIEW → PUBLISHED
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


async def _setup_filterable_category(admin_client: AsyncClient):
    """Create a category with a template, filterable attributes, and values.

    Returns a dict with IDs for: category, brands, attributes, values.
    """
    # Template
    template = await create_attribute_template(admin_client)

    # Attribute: color (filterable)
    color_attr = await create_attribute(
        admin_client,
        code="color",
        slug="color",
        name_i18n={"ru": "Цвет", "en": "Color"},
        is_filterable=True,
        level="product",
    )
    red = await create_attribute_value(
        admin_client,
        color_attr["id"],
        code="red",
        slug="red",
        value_i18n={"ru": "Красный", "en": "Red"},
    )
    blue = await create_attribute_value(
        admin_client,
        color_attr["id"],
        code="blue",
        slug="blue",
        value_i18n={"ru": "Синий", "en": "Blue"},
    )
    green = await create_attribute_value(
        admin_client,
        color_attr["id"],
        code="green",
        slug="green",
        value_i18n={"ru": "Зелёный", "en": "Green"},
    )

    # Attribute: material (filterable)
    material_attr = await create_attribute(
        admin_client,
        code="material",
        slug="material",
        name_i18n={"ru": "Материал", "en": "Material"},
        is_filterable=True,
        level="product",
    )
    cotton = await create_attribute_value(
        admin_client,
        material_attr["id"],
        code="cotton",
        slug="cotton",
        value_i18n={"ru": "Хлопок", "en": "Cotton"},
    )
    polyester = await create_attribute_value(
        admin_client,
        material_attr["id"],
        code="polyester",
        slug="polyester",
        value_i18n={"ru": "Полиэстер", "en": "Polyester"},
    )

    # Bind attributes to template
    await bind_attribute_to_template(admin_client, template["id"], color_attr["id"])
    await bind_attribute_to_template(admin_client, template["id"], material_attr["id"])

    # Category with template
    category = await create_category(admin_client, template_id=template["id"])

    # Brands
    brand_a = await create_brand(admin_client, name="Brand A", slug="brand-a")
    brand_b = await create_brand(admin_client, name="Brand B", slug="brand-b")

    return {
        "category": category,
        "template": template,
        "color_attr": color_attr,
        "material_attr": material_attr,
        "red": red,
        "blue": blue,
        "green": green,
        "cotton": cotton,
        "polyester": polyester,
        "brand_a": brand_a,
        "brand_b": brand_b,
    }


# ---------------------------------------------------------------------------
# Tests — EAV Attribute Filters
# ---------------------------------------------------------------------------


class TestStorefrontEAVFilters:
    """Tests for attr.* query parameter filtering on the PLP endpoint."""

    async def test_filter_by_single_attribute_value(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Filtering by attr.color=red returns only red products."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        # Product 1: red, cotton
        p1 = await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["red"]["id"]),
                (setup["material_attr"]["id"], setup["cotton"]["id"]),
            ],
        )
        # Product 2: blue, polyester
        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_b"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["blue"]["id"]),
                (setup["material_attr"]["id"], setup["polyester"]["id"]),
            ],
        )

        resp = await async_client.get(
            PLP,
            params={"category_id": cat_id, "attr.color": "red"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["slug"] == p1["slug"]

    async def test_filter_by_multiple_values_or_semantics(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Filtering attr.color=red&attr.color=blue returns both."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["red"]["id"]),
            ],
        )
        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["blue"]["id"]),
            ],
        )

        # Both red and blue products match
        resp = await async_client.get(
            f"{PLP}?category_id={cat_id}&attr.color=red&attr.color=blue",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2

    async def test_filter_by_two_different_attributes_and_semantics(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Filtering by two different attributes uses AND (both must match)."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        # Product 1: red + cotton
        p1 = await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["red"]["id"]),
                (setup["material_attr"]["id"], setup["cotton"]["id"]),
            ],
        )
        # Product 2: red + polyester
        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["red"]["id"]),
                (setup["material_attr"]["id"], setup["polyester"]["id"]),
            ],
        )

        resp = await async_client.get(
            f"{PLP}?category_id={cat_id}&attr.color=red&attr.material=cotton",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["slug"] == p1["slug"]

    async def test_filter_unknown_attribute_ignored(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Unknown attr.* params are silently dropped — returns all products."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
        )

        resp = await async_client.get(
            PLP,
            params={"category_id": cat_id, "attr.nonexistent": "foo"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1

    async def test_filter_no_results(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Filtering by an attribute value no product has returns empty list."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["red"]["id"]),
            ],
        )

        resp = await async_client.get(
            PLP,
            params={"category_id": cat_id, "attr.color": "green"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 0


# ---------------------------------------------------------------------------
# Tests — Faceted Counts (include_facets=true)
# ---------------------------------------------------------------------------


class TestStorefrontFacets:
    """Tests for include_facets=true on the PLP endpoint."""

    async def test_facets_returned_when_requested(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """include_facets=true returns facets alongside products."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["red"]["id"]),
            ],
        )

        resp = await async_client.get(
            PLP,
            params={"category_id": cat_id, "include_facets": "true"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "facets" in data
        assert data["facets"] is not None
        assert "attributeFacets" in data["facets"]
        assert "brandFacets" in data["facets"]
        assert "priceRange" in data["facets"]
        assert "totalProducts" in data["facets"]

    async def test_facets_not_returned_by_default(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """By default (no include_facets), facets is null."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
        )

        resp = await async_client.get(PLP, params={"category_id": cat_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("facets") is None

    async def test_facet_counts_correct(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Facet counts correctly reflect the number of products per value."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        # 2 red products, 1 blue product
        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["red"]["id"]),
            ],
        )
        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["red"]["id"]),
            ],
        )
        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_b"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["blue"]["id"]),
            ],
        )

        resp = await async_client.get(
            PLP,
            params={"category_id": cat_id, "include_facets": "true"},
        )
        assert resp.status_code == 200
        facets = resp.json()["facets"]

        # Find color facet group
        color_facet = next(
            (f for f in facets["attributeFacets"] if f["code"] == "color"),
            None,
        )
        assert color_facet is not None

        # Check counts
        value_counts = {v["slug"]: v["count"] for v in color_facet["values"]}
        assert value_counts.get("red") == 2
        assert value_counts.get("blue") == 1

        # Total products
        assert facets["totalProducts"] == 3

    async def test_brand_facet_counts(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Brand facet counts are correct."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        # 2 brand_a, 1 brand_b
        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
        )
        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
        )
        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_b"]["id"],
        )

        resp = await async_client.get(
            PLP,
            params={"category_id": cat_id, "include_facets": "true"},
        )
        assert resp.status_code == 200
        brand_facets = resp.json()["facets"]["brandFacets"]
        brand_counts = {b["slug"]: b["count"] for b in brand_facets}
        assert brand_counts.get("brand-a") == 2
        assert brand_counts.get("brand-b") == 1

    async def test_price_range_facet(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Price range reflects min/max across products."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            price=500_00,
        )
        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            price=2000_00,
        )

        resp = await async_client.get(
            PLP,
            params={"category_id": cat_id, "include_facets": "true"},
        )
        assert resp.status_code == 200
        pr = resp.json()["facets"]["priceRange"]
        assert pr is not None
        assert pr["minPrice"] == 500_00
        assert pr["maxPrice"] == 2000_00
        assert pr["currency"] == "RUB"

    async def test_facets_with_filter_applied(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """When a filter is applied, total_products reflects filtered count."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["red"]["id"]),
            ],
        )
        await _create_published_product(
            admin_client,
            category_id=cat_id,
            brand_id=setup["brand_a"]["id"],
            attribute_assignments=[
                (setup["color_attr"]["id"], setup["blue"]["id"]),
            ],
        )

        # Filter to red only, request facets
        resp = await async_client.get(
            f"{PLP}?category_id={cat_id}&attr.color=red&include_facets=true",
        )
        assert resp.status_code == 200
        data = resp.json()
        # Only 1 product in items (filtered)
        assert len(data["items"]) == 1
        # Total reflects filter
        assert data["facets"]["totalProducts"] == 1

    async def test_facets_empty_category(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session,
    ):
        """Facets on empty category return zero counts."""
        setup = await _setup_filterable_category(admin_client)
        cat_id = setup["category"]["id"]

        resp = await async_client.get(
            PLP,
            params={"category_id": cat_id, "include_facets": "true"},
        )
        assert resp.status_code == 200
        facets = resp.json()["facets"]
        assert facets["totalProducts"] == 0
        assert facets["priceRange"] is None
