"""Seed data for built-in suppliers.

Fixed UUIDv7 identifiers for marketplace and local suppliers.
These are deterministic across all environments.
"""

import uuid

from src.modules.supplier.domain.value_objects import SupplierType

# ---------------------------------------------------------------------------
# Cross-border marketplace suppliers
# ---------------------------------------------------------------------------
POIZON_ID = uuid.UUID("019550a0-0001-7000-8000-000000000001")
TAOBAO_ID = uuid.UUID("019550a0-0002-7000-8000-000000000002")
PINDUODUO_ID = uuid.UUID("019550a0-0003-7000-8000-000000000003")
ALI_1688_ID = uuid.UUID("019550a0-0004-7000-8000-000000000004")

# ---------------------------------------------------------------------------
# Local regional suppliers
# ---------------------------------------------------------------------------
MOSCOW_ID = uuid.UUID("019550a0-0005-7000-8000-000000000005")
SPB_ID = uuid.UUID("019550a0-0006-7000-8000-000000000006")
VOLGOGRAD_ID = uuid.UUID("019550a0-0007-7000-8000-000000000007")

SEED_SUPPLIERS: list[dict] = [
    # ── Cross-border ───────────────────────────────────────────────────
    {
        "id": POIZON_ID,
        "name": "Poizon",
        "type": SupplierType.CROSS_BORDER,
        "region": "China",
    },
    {
        "id": TAOBAO_ID,
        "name": "Taobao",
        "type": SupplierType.CROSS_BORDER,
        "region": "China",
    },
    {
        "id": PINDUODUO_ID,
        "name": "Pinduoduo",
        "type": SupplierType.CROSS_BORDER,
        "region": "China",
    },
    {
        "id": ALI_1688_ID,
        "name": "1688",
        "type": SupplierType.CROSS_BORDER,
        "region": "China",
    },
    # ── Local ──────────────────────────────────────────────────────────
    {
        "id": MOSCOW_ID,
        "name": "Москва",
        "type": SupplierType.LOCAL,
        "region": "Moscow",
    },
    {
        "id": SPB_ID,
        "name": "Санкт-Петербург",
        "type": SupplierType.LOCAL,
        "region": "Saint Petersburg",
    },
    {
        "id": VOLGOGRAD_ID,
        "name": "Волгоград",
        "type": SupplierType.LOCAL,
        "region": "Volgograd",
    },
]

# Backward-compatible alias
MARKETPLACE_SUPPLIERS = [
    s for s in SEED_SUPPLIERS if s["type"] == SupplierType.CROSS_BORDER
]
