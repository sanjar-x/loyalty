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
    # Resolve group codes -> IDs (groups created by management/sync_attributes)
    # If groups don't exist yet, create without group_id
    attr_ids: dict[str, str] = {}  # code -> id
    _attr_cache: dict[str, str] = {}  # lazy-loaded on first 409

    for attr in data["attributes"]:
        body: dict[str, Any] = {
            "code": attr["code"],
            "slug": attr["slug"],
            "nameI18N": attr["nameI18N"],
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
        if attr.get("descriptionI18N"):
            body["descriptionI18N"] = attr["descriptionI18N"]

        result = _post(ctx.client, f"{base}/catalog/attributes", ctx.token, body)
        if result:
            attr_ids[attr["code"]] = result["id"]
            print(f"    + {attr['code']:<20} {result['id']}")
        else:
            # Exists -> resolve ID from cache
            if not _attr_cache:
                _attr_cache.update(_load_all_attributes(ctx))
            existing = _attr_cache.get(attr["code"])
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
                "valueI18N": v["valueI18N"],
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
    template_ids: dict[str, str] = {}  # code -> id
    _tmpl_cache: dict[str, str] = {}  # lazy-loaded on first 409

    for tmpl in data.get("templates", []):
        result = _post(
            ctx.client,
            f"{base}/catalog/attribute-templates",
            ctx.token,
            {
                "code": tmpl["code"],
                "nameI18N": tmpl["nameI18N"],
                "sortOrder": tmpl.get("sortOrder", 0),
            },
        )
        if result:
            template_ids[tmpl["code"]] = result["id"]
            print(f"    + {tmpl['code']:<20} {result['id']}")
        else:
            if not _tmpl_cache:
                _tmpl_cache.update(_load_all_templates(ctx))
            existing = _tmpl_cache.get(tmpl["code"])
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
                print(
                    f"    ! {tmpl['code']}/{binding['attributeCode']}: attr not found"
                )
                continue
            result = _post(
                ctx.client,
                f"{base}/catalog/attribute-templates/{tmpl_id}/attributes",
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
    # On re-run, template_id may already be set on the root category.
    # UpdateCategoryHandler only runs CTE propagation when template_id
    # actually changes. To ensure children get effective_template_id
    # even on re-run, we do a clear->set cycle: PATCH null then PATCH id.
    # This forces template_id_changed=True and triggers CTE propagation.
    print("  [6/6] Category -> template assignment")
    cat_cache = _load_all_categories(ctx)
    for tmpl in data.get("templates", []):
        cat_slug = tmpl.get("assignToCategorySlug")
        tmpl_id = template_ids.get(tmpl["code"])
        if not cat_slug or not tmpl_id:
            continue

        cat_id = cat_cache.get(cat_slug)
        if not cat_id:
            print(f"    ! {cat_slug}: category not found")
            continue

        headers = {"Authorization": f"Bearer {ctx.token}"}
        patch_url = f"{base}/catalog/categories/{cat_id}"

        # Step A: clear template (forces change detection on next PATCH)
        ctx.client.patch(patch_url, json={"templateId": None}, headers=headers)

        # Step B: set template (triggers CTE propagation to all children)
        r = ctx.client.patch(patch_url, json={"templateId": tmpl_id}, headers=headers)
        if r.status_code == 200:
            print(f"    + {cat_slug} -> {tmpl['code']} (propagated)")
        else:
            print(f"    ! {cat_slug} -> {tmpl['code']}: {r.status_code}")


# ── Cached lookup helpers (single API call each) ──────────────────────


def _load_all_attributes(ctx: SeedContext) -> dict[str, str]:
    """code -> id"""
    items = _get_items(
        ctx.client, f"{ctx.api_prefix}/catalog/attributes?limit=200", ctx.token
    )
    return {item["code"]: item["id"] for item in items}


def _load_all_templates(ctx: SeedContext) -> dict[str, str]:
    """code -> id"""
    items = _get_items(
        ctx.client, f"{ctx.api_prefix}/catalog/attribute-templates?limit=200", ctx.token
    )
    return {item["code"]: item["id"] for item in items}


def _load_all_categories(ctx: SeedContext) -> dict[str, str]:
    """slug -> id"""
    items = _get_items(
        ctx.client, f"{ctx.api_prefix}/catalog/categories?limit=200", ctx.token
    )
    return {item["slug"]: item["id"] for item in items}
