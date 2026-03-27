"""Seed brands via HTTP API.

Called by seed/main.py as part of the seeding flow.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from seed.main import SeedContext

DATA_FILE = Path(__file__).parent / "brands.json"


def seed_brands(ctx: SeedContext) -> None:
    brands = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    headers = {"Authorization": f"Bearer {ctx.token}"}
    url = f"{ctx.api_prefix}/catalog/brands"
    created = skipped = failed = 0

    for brand in brands:
        r = ctx.client.post(url, json=brand, headers=headers)

        if r.status_code == 201:
            print(f"    + {brand['name']:<20} {r.json()['id']}")
            created += 1
        elif r.status_code == 409:
            print(f"    ~ {brand['name']:<20} (exists)")
            skipped += 1
        else:
            print(f"    ! {brand['name']:<20} {r.status_code} {r.text[:80]}")
            failed += 1

    print(f"  --- {created} created, {skipped} skipped, {failed} failed")
