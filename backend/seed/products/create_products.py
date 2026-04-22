"""Seed products with SKUs and attribute assignments via HTTP API.

Resolves brand/category/attribute references by slug at runtime,
then creates each product with its SKUs and product-level attributes.

Called by seed/main.py as part of the seeding flow.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from seed.main import SeedContext

DATA_FILE = Path(__file__).parent / "products.json"


def _get(client: Any, url: str, token: str) -> dict:
    r = client.get(url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()


def _post(client: Any, url: str, token: str, body: dict) -> dict | None:
    r = client.post(url, json=body, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 201:
        return r.json()
    if r.status_code == 409:
        return None  # already exists
    r.raise_for_status()
    return None


def _load_lookup(ctx: SeedContext, path: str, key: str) -> dict[str, str]:
    """Fetch a paginated list and build slug->id lookup."""
    data = _get(ctx.client, f"{ctx.api_prefix}{path}?limit=200", ctx.token)
    return {item[key]: item["id"] for item in data["items"]}


def _load_attribute_values(ctx: SeedContext, attr_id: str) -> dict[str, str]:
    """Fetch attribute values and build code->id lookup."""
    data = _get(
        ctx.client,
        f"{ctx.api_prefix}/catalog/attributes/{attr_id}/values?limit=200",
        ctx.token,
    )
    return {item["code"]: item["id"] for item in data["items"]}


def seed_products(ctx: SeedContext) -> None:
    products = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    # 1. Build lookups
    print("  Loading references...")
    brands = _load_lookup(ctx, "/catalog/brands", "slug")
    categories = _load_lookup(ctx, "/catalog/categories", "slug")
    attributes = _load_lookup(ctx, "/catalog/attributes", "code")

    # Pre-load attribute values for all referenced attributes
    attr_values: dict[str, dict[str, str]] = {}  # attr_code -> {value_code -> id}
    for attr_code, attr_id in attributes.items():
        attr_values[attr_code] = _load_attribute_values(ctx, attr_id)

    print(
        f"  Resolved: {len(brands)} brands, {len(categories)} categories, "
        f"{len(attributes)} attributes\n"
    )

    created = skipped = failed = 0

    for p in products:
        brand_id = brands.get(p["brandSlug"])
        category_id = categories.get(p["categorySlug"])

        if not brand_id:
            print(f"  ! {p['slug']:<30} brand '{p['brandSlug']}' not found")
            failed += 1
            continue
        if not category_id:
            print(f"  ! {p['slug']:<30} category '{p['categorySlug']}' not found")
            failed += 1
            continue

        # 2. Create product (or resolve existing by slug on 409)
        result = _post(
            ctx.client,
            f"{ctx.api_prefix}/catalog/products",
            ctx.token,
            {
                "titleI18N": p["titleI18N"],
                "slug": p["slug"],
                "brandId": brand_id,
                "primaryCategoryId": category_id,
                "descriptionI18N": p.get("descriptionI18N", {}),
                "tags": p.get("tags", []),
            },
        )

        if result is None:
            # Product already exists — resolve id + default variant by slug
            # so we can still upsert attributes and SKUs on re-run.
            existing = _resolve_product_by_slug(ctx, p["slug"])
            if existing is None:
                print(f"  ! {p['slug']:<30} exists but could not be resolved")
                failed += 1
                continue
            product_id, variant_id = existing
            print(f"  ~ {p['slug']:<30} (exists) — upserting attrs/skus")
            skipped += 1
        else:
            product_id = result["id"]
            variant_id = result["defaultVariantId"]
            print(f"  + {p['slug']:<30} {product_id}")
            created += 1

        # 3. Assign product-level attributes (idempotent via 409)
        attr_assignments = p.get("attributes", {})
        for attr_code, value_code in attr_assignments.items():
            attr_id = attributes.get(attr_code)
            value_id = attr_values.get(attr_code, {}).get(value_code)

            if not attr_id or not value_id:
                print(f"      ! attr {attr_code}={value_code} — not found, skipping")
                continue

            resp = _post(
                ctx.client,
                f"{ctx.api_prefix}/catalog/products/{product_id}/attributes",
                ctx.token,
                {"attributeId": attr_id, "attributeValueId": value_id},
            )
            if resp:
                print(f"      attr {attr_code}={value_code}")

        # 4. Create SKUs (idempotent via 409 on skuCode)
        for sku in p.get("skus", []):
            variant_attributes = []
            for attr_code, value_code in sku.get("variantAttrs", {}).items():
                attr_id = attributes.get(attr_code)
                value_id = attr_values.get(attr_code, {}).get(value_code)
                if attr_id and value_id:
                    variant_attributes.append({
                        "attributeId": attr_id,
                        "attributeValueId": value_id,
                    })

            sku_body: dict[str, Any] = {
                "skuCode": sku["code"],
                "isActive": True,
                "variantAttributes": variant_attributes,
            }
            if sku.get("price") is not None:
                sku_body["priceAmount"] = sku["price"]
                sku_body["priceCurrency"] = sku.get("currency", "RUB")

            sku_result = _post(
                ctx.client,
                f"{ctx.api_prefix}/catalog/products/{product_id}/variants/{variant_id}/skus",
                ctx.token,
                sku_body,
            )
            if sku_result:
                print(f"      sku {sku['code']:<20} {sku_result['id']}")

    print(f"\n  --- {created} created, {skipped} skipped, {failed} failed")


def _resolve_product_by_slug(
    ctx: SeedContext, slug: str
) -> tuple[str, str] | None:
    """Fetch (product_id, default_variant_id) for an existing product.

    Used on re-runs: ``POST /products`` returns 409 for an existing slug
    but we still need ``defaultVariantId`` to create/update SKUs. The
    product list endpoint returns the variant summary we need.
    """
    r = ctx.client.get(
        f"{ctx.api_prefix}/catalog/products",
        params={"slug": slug, "limit": 1},
        headers={"Authorization": f"Bearer {ctx.token}"},
    )
    if r.status_code != 200:
        return None
    items = r.json().get("items", [])
    if not items:
        return None
    prod = items[0]
    variant_id = prod.get("defaultVariantId") or (
        prod.get("defaultVariant") or {}
    ).get("id")
    if not variant_id:
        # Fallback: detail endpoint
        detail = ctx.client.get(
            f"{ctx.api_prefix}/catalog/products/{prod['id']}",
            headers={"Authorization": f"Bearer {ctx.token}"},
        )
        if detail.status_code == 200:
            body = detail.json()
            variant_id = body.get("defaultVariantId") or (
                body.get("defaultVariant") or {}
            ).get("id")
    if not variant_id:
        return None
    return prod["id"], variant_id
