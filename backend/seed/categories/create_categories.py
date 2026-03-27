"""Seed categories via single-item HTTP API (no bulk endpoint dependency).

Creates root categories first, fetches their IDs, then creates children.
Uses slug-based duplicate detection: existing categories are skipped.

Called by seed/main.py as part of the seeding flow.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from seed.main import SeedContext

DATA_FILE = Path(__file__).parent / "categories.json"


def seed_categories(ctx: SeedContext) -> None:
    items = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    headers = {"Authorization": f"Bearer {ctx.token}"}
    url = f"{ctx.api_prefix}/catalog/categories"

    # ref → id (resolved at creation time)
    ref_map: dict[str, str] = {}
    created = skipped = failed = 0

    for item in items:
        # Resolve parent
        parent_id = None
        if item.get("parentRef"):
            parent_id = ref_map.get(item["parentRef"])
            if not parent_id:
                # Parent was skipped → try to find it in DB
                parent_id = _find_category_by_slug(ctx, item["parentRef"])
                if not parent_id:
                    print(
                        f"    ! {item['slug']:<25} parent '{item['parentRef']}' not found"
                    )
                    failed += 1
                    continue

        body = {
            "nameI18n": item["nameI18n"],
            "slug": item["slug"],
            "sortOrder": item.get("sortOrder", 0),
        }
        if parent_id:
            body["parentId"] = parent_id
        if item.get("templateId"):
            body["templateId"] = item["templateId"]

        r = ctx.client.post(url, json=body, headers=headers)

        if r.status_code == 201:
            cat_id = r.json()["id"]
            ref = item.get("ref")
            if ref:
                ref_map[ref] = cat_id
            level = "L0" if not parent_id else "L1"
            print(f"    + {item['slug']:<25} {cat_id} ({level})")
            created += 1
        elif r.status_code == 409:
            # Exists → resolve ID for children
            ref = item.get("ref")
            if ref:
                found_id = _find_category_by_slug(ctx, item["slug"])
                if found_id:
                    ref_map[ref] = found_id
            print(f"    ~ {item['slug']:<25} (exists)")
            skipped += 1
        else:
            print(f"    ! {item['slug']:<25} {r.status_code} {r.text[:80]}")
            failed += 1

    print(f"  --- {created} created, {skipped} skipped, {failed} failed")


def _find_category_by_slug(ctx: SeedContext, slug: str) -> str | None:
    """Find category ID by slug via list endpoint."""
    r = ctx.client.get(
        f"{ctx.api_prefix}/catalog/categories?limit=200",
        headers={"Authorization": f"Bearer {ctx.token}"},
    )
    if r.status_code != 200:
        return None
    for cat in r.json()["items"]:
        if cat["slug"] == slug:
            return cat["id"]
    return None
