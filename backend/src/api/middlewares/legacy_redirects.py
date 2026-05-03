"""Legacy URL redirect middleware (2026-05 router restructure).

Issues a 308 Permanent Redirect from old URL paths to their new namespaces
so existing clients have a 7-day window to migrate without breakage.
After 2026-05-09 this middleware should be removed; the architecture
fitness test ``tests/architecture/test_router_audience.py`` already
prevents regressions.

Migration map mirrors ``docs/api/router-restructure-2026-05.md``.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

# Mapping of OLD prefix → NEW prefix. Order matters: the first match
# wins, so put more specific paths above broader ones.
#
# Each entry is a regex anchored at the start of the path. Use named
# capture groups to forward path parameters.
_REDIRECTS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Order webhooks → /webhooks/dobropost
    (
        re.compile(r"^/api/v1/orders/webhooks/dobropost(?P<rest>/.*)?$"),
        r"/api/v1/webhooks/dobropost\g<rest>",
    ),
    # Logistics webhooks → /webhooks/logistics
    (
        re.compile(r"^/api/v1/logistics/webhooks(?P<rest>/.*)?$"),
        r"/api/v1/webhooks/logistics\g<rest>",
    ),
    # Payment webhooks → /webhooks/payments
    (
        re.compile(r"^/api/v1/payments/webhooks(?P<rest>/.*)?$"),
        r"/api/v1/webhooks/payments\g<rest>",
    ),
    # /profile/me/sessions → /profile/sessions
    (re.compile(r"^/api/v1/profile/me/sessions$"), r"/api/v1/profile/sessions"),
    # /profile/me/password → /profile/password
    (re.compile(r"^/api/v1/profile/me/password$"), r"/api/v1/profile/password"),
    # /catalog/storefront/* → /storefront/*
    (
        re.compile(r"^/api/v1/catalog/storefront(?P<rest>/.*)?$"),
        r"/api/v1/storefront\g<rest>",
    ),
    # /catalog/<resource>/* (admin) → /admin/catalog/<resource>/*
    # Covers: brands, categories, products, attributes, attribute-groups,
    #         attribute-templates.
    (
        re.compile(
            r"^/api/v1/catalog/(?P<resource>brands|categories|products|attributes|attribute-groups|attribute-templates)(?P<rest>/.*)?$"
        ),
        r"/api/v1/admin/catalog/\g<resource>\g<rest>",
    ),
    # /pricing/* → /admin/pricing/*
    (re.compile(r"^/api/v1/pricing(?P<rest>/.*)?$"), r"/api/v1/admin/pricing\g<rest>"),
    # /suppliers/* → /admin/suppliers/*
    (
        re.compile(r"^/api/v1/suppliers(?P<rest>/.*)?$"),
        r"/api/v1/admin/suppliers\g<rest>",
    ),
    # /logistics/quotes, /logistics/shipments etc. → /admin/logistics/*
    # NOTE: must come AFTER /logistics/webhooks rule above.
    (
        re.compile(r"^/api/v1/logistics/(?P<rest>(?!webhooks).*)$"),
        r"/api/v1/admin/logistics/\g<rest>",
    ),
)


class LegacyRedirectsMiddleware(BaseHTTPMiddleware):
    """Translate legacy URLs to the post-2026-05 layout via 308 redirects."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        for pattern, replacement in _REDIRECTS:
            new_path, n = pattern.subn(replacement, path)
            if n:
                target = request.url.replace(path=new_path)
                return RedirectResponse(url=str(target), status_code=308)
        return await call_next(request)
