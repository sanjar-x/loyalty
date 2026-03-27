"""Seed attribute groups, attributes, values, templates, and bindings via HTTP API.

Flow:
  1. Create attribute groups
  2. Create attributes (resolve group by code)
  3. Create attribute values (bulk per attribute)
  4. Create attribute templates
  5. Bind attributes to templates
  6. Assign templates to root categories (PATCH category.templateId)

Called by seed/main.py as part of the seeding flow.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from seed.main import SeedContext

DATA_FILE = Path(__file__).parent / "attributes.json"


def _post(client: Any, url: str, token: str, body: dict) -> dict | None:
    r = client.post(url, json=body, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 201:
        return r.json()
    if r.status_code == 409:
        return None
    r.raise_for_status()
    return None


def _get_items(client: Any, url: str, token: str) -> list[dict]:
    r = client.get(url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()["items"]


def seed_attributes(ctx: SeedContext) -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    base = ctx.api_prefix

    # ── 1. Attribute groups ────────────────────────────────────────────
    print("  [1/6] Attribute groups")
    # Groups are seed-only (no CRUD endpoint) — created by sync_attributes.
    # We just verify they exist via list attributes later.

    # ── 2. Attributes ──────────────────────────────────────────────────
    print("  [2/6] Attributes")
    # Resolve group codes → IDs (groups created by management/sync_attributes)
    # If groups don't exist yet, create without group_id
    attr_ids: dict[str, str] = {}  # code → id

    for attr in data["attributes"]:
        body: dict[str, Any] = {
            "code": attr["code"],
            "slug": attr["slug"],
            "nameI18n": attr["nameI18n"],
            "dataType": attr["dataType"],
            "uiType": attr["uiType"],
            "isDictionary": attr.get("isDictionary", True),
            "level": attr.get("level", "product"),
            "isFilterable": attr.get("isFilterable", False),
            "isSearchable": attr.get("isSearchable", False),
            "searchWeight": attr.get("searchWeight", 5),
            "isComparable": attr.get("isComparable", False),
            "isVisibleOnCard": attr.get("isVisibleOnCard", False),
        }
        if attr.get("descriptionI18n"):
            body["descriptionI18n"] = attr["descriptionI18n"]

        result = _post(ctx.client, f"{base}/catalog/attributes", ctx.token, body)
        if result:
            attr_ids[attr["code"]] = result["id"]
            print(f"    + {attr['code']:<20} {result['id']}")
        else:
            # Exists → resolve ID
            existing = _find_attribute_by_code(ctx, attr["code"])
            if existing:
                attr_ids[attr["code"]] = existing
                print(f"    ~ {attr['code']:<20} (exists)")
            else:
                print(f"    ! {attr['code']:<20} failed to resolve")

    # ── 3. Attribute values ────────────────────────────────────────────
    print("  [3/6] Attribute values")
    for attr in data["attributes"]:
        values = attr.get("values", [])
        if not values:
            continue
        attr_id = attr_ids.get(attr["code"])
        if not attr_id:
            print(f"    ! {attr['code']}: no ID, skipping values")
            continue

        bulk_items = []
        for v in values:
            item: dict[str, Any] = {
                "code": v["code"],
                "slug": v["slug"],
                "valueI18n": v["valueI18n"],
                "sortOrder": v.get("sortOrder", 0),
            }
            if v.get("metaData"):
                item["metaData"] = v["metaData"]
            bulk_items.append(item)

        result = _post(
            ctx.client,
            f"{base}/catalog/attributes/{attr_id}/values/bulk",
            ctx.token,
            {"items": bulk_items},
        )
        if result:
            print(f"    + {attr['code']:<20} {result['createdCount']} values")
        else:
            print(f"    ~ {attr['code']:<20} values exist")

    # ── 4. Attribute templates ─────────────────────────────────────────
    print("  [4/6] Templates")
    template_ids: dict[str, str] = {}  # code → id

    for tmpl in data.get("templates", []):
        result = _post(
            ctx.client,
            f"{base}/catalog/attribute-templates",
            ctx.token,
            {
                "code": tmpl["code"],
                "nameI18n": tmpl["nameI18n"],
                "sortOrder": tmpl.get("sortOrder", 0),
            },
        )
        if result:
            template_ids[tmpl["code"]] = result["id"]
            print(f"    + {tmpl['code']:<20} {result['id']}")
        else:
            existing = _find_template_by_code(ctx, tmpl["code"])
            if existing:
                template_ids[tmpl["code"]] = existing
                print(f"    ~ {tmpl['code']:<20} (exists)")

    # ── 5. Template-attribute bindings ─────────────────────────────────
    print("  [5/6] Bindings")
    for tmpl in data.get("templates", []):
        tmpl_id = template_ids.get(tmpl["code"])
        if not tmpl_id:
            continue
        for binding in tmpl.get("bindings", []):
            attr_id = attr_ids.get(binding["attributeCode"])
            if not attr_id:
                print(f"    ! {tmpl['code']}/{binding['attributeCode']}: attr not found")
                continue
            result = _post(
                ctx.client,
                f"{base}/catalog/attribute-templates/{tmpl_id}/bindings",
                ctx.token,
                {
                    "attributeId": attr_id,
                    "sortOrder": binding.get("sortOrder", 0),
                    "requirementLevel": binding.get("requirementLevel", "optional"),
                },
            )
            if result:
                print(f"    + {tmpl['code']}/{binding['attributeCode']}")
            else:
                print(f"    ~ {tmpl['code']}/{binding['attributeCode']} (exists)")

    # ── 6. Assign templates to categories ──────────────────────────────
    print("  [6/6] Category → template assignment")
    for tmpl in data.get("templates", []):
        cat_slug = tmpl.get("assignToCategorySlug")
        tmpl_id = template_ids.get(tmpl["code"])
        if not cat_slug or not tmpl_id:
            continue

        cat_id = _find_category_by_slug(ctx, cat_slug)
        if not cat_id:
            print(f"    ! {cat_slug}: category not found")
            continue

        r = ctx.client.patch(
            f"{base}/catalog/categories/{cat_id}",
            json={"templateId": tmpl_id},
            headers={"Authorization": f"Bearer {ctx.token}"},
        )
        if r.status_code == 200:
            print(f"    + {cat_slug} → {tmpl['code']}")
        else:
            print(f"    ! {cat_slug} → {tmpl['code']}: {r.status_code}")


# ── Lookup helpers ─────────────────────────────────────────────────────


def _find_attribute_by_code(ctx: SeedContext, code: str) -> str | None:
    items = _get_items(
        ctx.client, f"{ctx.api_prefix}/catalog/attributes?limit=200", ctx.token
    )
    for item in items:
        if item["code"] == code:
            return item["id"]
    return None


def _find_template_by_code(ctx: SeedContext, code: str) -> str | None:
    items = _get_items(
        ctx.client, f"{ctx.api_prefix}/catalog/attribute-templates?limit=200", ctx.token
    )
    for item in items:
        if item["code"] == code:
            return item["id"]
    return None


def _find_category_by_slug(ctx: SeedContext, slug: str) -> str | None:
    items = _get_items(
        ctx.client, f"{ctx.api_prefix}/catalog/categories?limit=200", ctx.token
    )
    for item in items:
        if item["slug"] == slug:
            return item["id"]
    return None
