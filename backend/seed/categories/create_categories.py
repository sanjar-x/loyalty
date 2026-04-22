"""Seed categories via single-item HTTP API.

Creates root categories first, fetches their IDs, then creates children.
Idempotent: existing categories are skipped but their IDs are resolved
for child references. Lookup results are cached to avoid N+1 API calls.

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

    # Pre-load existing categories (for re-run idempotency)
    slug_to_id = _load_all_categories(ctx)

    ref_map: dict[str, str] = {}
    created = skipped = failed = 0

    for item in items:
        # Resolve parent
        parent_id = None
        if item.get("parentRef"):
            parent_id = ref_map.get(item["parentRef"])
            if not parent_id:
                parent_id = slug_to_id.get(item["parentRef"])
            if not parent_id:
                print(
                    f"    ! {item['slug']:<25} parent '{item['parentRef']}' not found"
                )
                failed += 1
                continue

        body: dict = {
            "nameI18N": item["nameI18N"],
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
            slug_to_id[item["slug"]] = cat_id
            if item.get("ref"):
                ref_map[item["ref"]] = cat_id
            level = "L0" if not parent_id else "L1"
            print(f"    + {item['slug']:<25} {cat_id} ({level})")
            created += 1
        elif r.status_code == 409:
            existing_id = slug_to_id.get(item["slug"])
            if item.get("ref") and existing_id:
                ref_map[item["ref"]] = existing_id
            print(f"    ~ {item['slug']:<25} (exists)")
            skipped += 1
        else:
            print(f"    ! {item['slug']:<25} {r.status_code} {r.text[:80]}")
            failed += 1

    print(f"  --- {created} created, {skipped} skipped, {failed} failed")


def _load_all_categories(ctx: SeedContext) -> dict[str, str]:
    """Pre-load all categories into slug->id cache (single API call)."""
    r = ctx.client.get(
        f"{ctx.api_prefix}/catalog/categories?limit=200",
        headers={"Authorization": f"Bearer {ctx.token}"},
    )
    if r.status_code != 200:
        return {}
    return {cat["slug"]: cat["id"] for cat in r.json()["items"]}
