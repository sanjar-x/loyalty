"""Root API router that aggregates all module-level routers.

REFACT-001 PR-5: routers are iterated from
:data:`src.bootstrap.modules.MODULES` -- each
:class:`~src.bootstrap.module_registry.ModuleManifest` exposes its
routers in audience order (customer → admin → webhooks) via the
``routers`` property. Adding a router becomes a one-line change in
the owning module's ``module.py``; this aggregator does not need to
be touched.

The audience-based URL convention documented in
``docs/api/router-restructure-2026-05.md`` and enforced by
``tests/architecture/test_router_audience.py``:

* **Customer App** -- ``/api/v1/<resource>`` (storefront, cart, orders, ...).
* **Admin Panel**  -- ``/api/v1/admin/<module>/<resource>`` (staff-only).
* **Webhooks**     -- ``/api/v1/webhooks/<provider>`` (server-to-server).

Each router defines its own full prefix; ``include_router`` here MUST
NOT pass ``prefix=...`` -- that would double-namespace the URL.
"""

from fastapi import APIRouter

from src.bootstrap.modules import MODULES

router = APIRouter()

for _manifest in MODULES:
    for _module_router in _manifest.routers:
        router.include_router(_module_router)
