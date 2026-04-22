"""Entry point for seeding the Loyality backend.

Steps fall into two groups:

* **DB-only** (no HTTP server required): ``roles``, ``admin``, ``geo``
* **API-only** (HTTP server must be running): ``brands``, ``categories``,
  ``attributes``, ``products``

Usage
-----
::

    # Everything (server must be running for API steps).
    uv run python -m seed.main

    # DB-only steps — no server needed.
    uv run python -m seed.main --step roles,admin,geo

    # API-only steps — server must be running, admin must already exist.
    uv run python -m seed.main --step brands,products

``--step`` accepts a comma-separated subset of step names. Order of
execution is always the canonical order defined in ``STEPS``, regardless
of how the user orders their argument.

Default admin credentials are loaded from ``seed/admin/admin.json``
(single source of truth). The CLI ``--login`` / ``--password`` flags
override them when you need to bootstrap a non-default admin.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from seed.admin.create_admin_user import seed_admin
from seed.attributes.create_attributes import seed_attributes
from seed.brands.create_brands import seed_brands
from seed.categories.create_categories import seed_categories
from seed.geo.create_currencies import seed_geo
from seed.products.create_products import seed_products
from seed.roles.create_roles import seed_roles

DEFAULT_BASE_URL = "https://loyalty-backend.up.railway.app"
API_PREFIX = "/api/v1"

_ADMIN_JSON = Path(__file__).parent / "admin" / "admin.json"


def _admin_defaults() -> dict:
    return json.loads(_ADMIN_JSON.read_text(encoding="utf-8"))


@dataclass
class SeedContext:
    """Shared state passed to every step.

    ``client`` and ``token`` are only populated when at least one API
    step is requested; DB-only steps never touch them.

    ``api_prefix`` is the path prefix under which the API is mounted
    (``/api/v1``). API-step modules build URLs as
    ``f"{ctx.api_prefix}/catalog/..."`` against ``ctx.client`` whose
    ``base_url`` is the host root — so the full URL is resolved
    relative to ``base_url``.
    """

    base_url: str
    login: str
    password: str
    api_prefix: str = API_PREFIX
    client: httpx.Client | None = None
    token: str | None = None
    data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Step:
    """Single unit of seed work.

    ``deps`` lists step names that MUST have completed before this one
    can safely run. When the user selects a subset via ``--step``, any
    missing transitive deps are auto-prepended (apt-style) so that
    referential integrity is preserved:

    * ``admin`` depends on ``roles`` — FK to ``roles.id`` via
      ``identity_roles``. Running ``--step admin`` alone would
      otherwise fail with a foreign-key violation on first-time seeds.
    * ``brands/categories/attributes/products`` depend on ``admin``
      being present — the step ``_login`` call authenticates as that
      admin and fails without it.
    * ``products`` depends on ``brands``, ``categories``, ``attributes``
      and ``geo`` (SKU ``priceCurrency`` FK).
    * ``attributes`` depends on ``categories`` — phase 6 assigns
      templates to root categories by slug.
    """

    name: str
    run: Callable[[SeedContext], None]
    db_only: bool
    deps: tuple[str, ...] = ()


# Canonical execution order — respected regardless of --step ordering.
STEPS: list[Step] = [
    Step("roles", seed_roles, db_only=True),
    Step("admin", seed_admin, db_only=True, deps=("roles",)),
    Step("geo", seed_geo, db_only=True),
    Step("brands", seed_brands, db_only=False, deps=("admin",)),
    Step("categories", seed_categories, db_only=False, deps=("admin",)),
    Step("attributes", seed_attributes, db_only=False, deps=("admin", "categories")),
    Step(
        "products",
        seed_products,
        db_only=False,
        deps=("admin", "geo", "brands", "categories", "attributes"),
    ),
]

STEP_NAMES = [s.name for s in STEPS]
STEPS_BY_NAME = {s.name: s for s in STEPS}


def _login(ctx: SeedContext) -> None:
    """Authenticate against the running API and cache the token.

    Raises on any non-2xx response so API steps fail fast rather
    than silently skipping.
    """
    assert ctx.client is not None
    resp = ctx.client.post(
        f"{ctx.api_prefix}/auth/login",
        json={"login": ctx.login, "password": ctx.password},
    )
    resp.raise_for_status()
    payload = resp.json()
    token = (
        payload.get("accessToken")
        or payload.get("access_token")
        or payload.get("data", {}).get("accessToken")
        or payload.get("data", {}).get("access_token")
    )
    if not token:
        raise RuntimeError(f"No access_token in login response: {payload}")
    ctx.token = token
    ctx.client.headers["Authorization"] = f"Bearer {token}"


def _parse_steps(raw: str | None) -> list[Step]:
    if not raw:
        return list(STEPS)
    requested = {s.strip() for s in raw.split(",") if s.strip()}
    unknown = requested - set(STEP_NAMES)
    if unknown:
        raise SystemExit(
            f"Unknown step(s): {', '.join(sorted(unknown))}. "
            f"Valid: {', '.join(STEP_NAMES)}"
        )

    # Transitive dep closure — apt-style implicit inclusion.
    # Each step's dependencies are also guaranteed to re-run so that
    # generated IDs (brands.id, categories.id, attribute_values.id, etc.)
    # are resolvable by downstream steps on a fresh database.
    closure: set[str] = set(requested)
    to_visit = list(requested)
    while to_visit:
        name = to_visit.pop()
        for dep in STEPS_BY_NAME[name].deps:
            if dep not in closure:
                closure.add(dep)
                to_visit.append(dep)

    added = sorted(closure - requested)
    if added:
        print(
            f"ℹ Auto-including transitive deps: {', '.join(added)} "
            f"(required by {', '.join(sorted(requested))})"
        )

    return [s for s in STEPS if s.name in closure]


def main() -> None:
    defaults = _admin_defaults()

    parser = argparse.ArgumentParser(description="Seed the Loyality backend.")
    parser.add_argument(
        "--step",
        help=f"Comma-separated subset of steps to run. Default: all. Valid: {', '.join(STEP_NAMES)}",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--login", default=defaults["email"])
    parser.add_argument("--password", default=defaults["password"])
    args = parser.parse_args()

    steps = _parse_steps(args.step)
    ctx = SeedContext(
        base_url=args.base_url, login=args.login, password=args.password
    )
    needs_api = any(not s.db_only for s in steps)

    if needs_api:
        ctx.client = httpx.Client(base_url=ctx.base_url, timeout=30.0)
        try:
            print(f"→ Logging in as {ctx.login} @ {ctx.base_url}")
            _login(ctx)
        except httpx.HTTPError as exc:
            print(f"✗ Login failed — is the server running at {ctx.base_url}? {exc}")
            if ctx.client is not None:
                ctx.client.close()
            sys.exit(1)

    try:
        for step in steps:
            mode = "DB" if step.db_only else "API"
            print(f"→ [{mode}] Seeding: {step.name}")
            step.run(ctx)
        print("✓ Seed complete.")
    finally:
        if ctx.client is not None:
            ctx.client.close()


if __name__ == "__main__":
    main()
