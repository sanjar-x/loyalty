"""Marketplace supplier seed data.

Fixed UUIDv7 identifiers for the four known Chinese marketplace suppliers.
These are deterministic across all environments.
"""

import uuid

from src.modules.supplier.domain.value_objects import SupplierType

# Fixed UUIDv7 identifiers — generated once, used everywhere
POIZON_ID = uuid.UUID("019550a0-0001-7000-8000-000000000001")
TAOBAO_ID = uuid.UUID("019550a0-0002-7000-8000-000000000002")
PINDUODUO_ID = uuid.UUID("019550a0-0003-7000-8000-000000000003")
ALI_1688_ID = uuid.UUID("019550a0-0004-7000-8000-000000000004")

MARKETPLACE_SUPPLIERS: list[dict] = [
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
]
