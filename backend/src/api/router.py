"""Root API router that aggregates all module-level routers.

Each bounded-context module declares its routers in a
:class:`ModuleManifest` (``src/modules/<name>/module.py``); this file
mounts them in the order required by the URL convention documented in
``docs/api/router-restructure-2026-05.md`` and enforced by
``tests/architecture/test_router_audience.py``:

* **Customer App** — `/api/v1/<resource>` (storefront, cart, orders, ...).
* **Admin Panel**  — `/api/v1/admin/<module>/<resource>` (staff-only).
* **Webhooks**     — `/api/v1/webhooks/<provider>` (server-to-server).

The routers themselves carry the full URL prefix, so ``include_router``
MUST NOT pass ``prefix=...`` here — that would double-namespace the
URL.
"""

from fastapi import APIRouter

from src.bootstrap.modules import MODULES

router = APIRouter()

# Mount in audience order so the OpenAPI schema and the local debug
# routes table read top-down by audience.
for _audience in ("customer_routers", "admin_routers", "webhook_routers"):
    for _manifest in MODULES:
        for _module_router in getattr(_manifest, _audience):
            router.include_router(_module_router)
