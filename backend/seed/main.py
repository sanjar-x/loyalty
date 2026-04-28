"""Entry point for seeding the Loyality backend.

Steps fall into two groups:

* **DB-only** (no HTTP server required): ``roles``, ``admin``, ``pricing``,
  ``logistics``
* **API-only** (HTTP server must be running): ``geo``, ``brands``,
  ``categories``, ``attributes``

Usage
-----
::

    # Everything (server must be running for API steps).
    uv run python -m seed.main

    # DB-only steps — no server needed.
    uv run python -m seed.main --step roles,admin,pricing

    # API-only steps — server must be running, admin must already exist.
    uv run python -m seed.main --step brands,categories,attributes

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
from seed.logistics.seed_cdek import seed_cdek
from seed.logistics.seed_yandex_delivery import seed_yandex_delivery
from seed.pricing.seed_pricing import seed_pricing
from seed.pricing.seed_pricing_config import seed_pricing_config
from seed.roles.create_roles import seed_roles
from seed.suppliers.seed_suppliers import seed_suppliers

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
    * ``brands/categories/attributes`` depend on ``admin``
      being present — the step ``_login`` call authenticates as that
      admin and fails without it.
    * ``attributes`` depends on ``categories`` — phase 6 assigns
      templates to root categories by slug.
    """

    name: str
    run: Callable[[SeedContext], None]
    db_only: bool
    deps: tuple[str, ...] = ()


def _seed_logistics(ctx: SeedContext) -> None:
    """Run all logistics provider seeders sequentially.

    Each individual seeder is idempotent and self-skipping when its
    credentials are not configured, so it is safe to call them all in a
    single ``logistics`` step regardless of which providers are active
    on the current environment.
    """
    seed_cdek(ctx)
    seed_yandex_delivery(ctx)


# Canonical execution order — respected regardless of --step ordering.
STEPS: list[Step] = [
    Step("roles", seed_roles, db_only=True),
    Step("admin", seed_admin, db_only=True, deps=("roles",)),
    # ADR-005 — pricing system variables (purchase_price_rub /
    # purchase_price_cny / fx_cny_rub). DB-only and idempotent on the
    # unique ``code`` index, so re-running is safe. No deps: the
    # variable registry is self-contained.
    Step("pricing", seed_pricing, db_only=True),
    # Logistics provider accounts (CDEK + Yandex Delivery). DB-only and
    # idempotent on ``provider_code`` — re-running updates each row's
    # credentials/config in place. Each provider is skipped gracefully
    # when its env credentials for the active ENVIRONMENT are unset
    # (CDEK_*_ACCOUNT / CDEK_*_SECURE_PASSWORD,
    # YANDEX_DELIVERY_*_OAUTH_TOKEN), so a partially-configured
    # environment seeds only what it has keys for.
    Step("logistics", _seed_logistics, db_only=True),
    Step("geo", seed_geo, db_only=False, deps=("admin",)),
    # Marketplace + local suppliers (Poizon, Taobao, Pinduoduo, 1688 +
    # local Алексей/Дмитрий/Руслан). DB-only and idempotent on
    # ``suppliers.id``. Cross-border rows reference ``country_code='CN'``,
    # so the ``geo`` step must seed China first — hence ``deps=("geo",)``.
    Step("suppliers", seed_suppliers, db_only=True, deps=("geo",)),
    # Pricing pipeline configuration: contexts (cross_border_cn / local_ru),
    # published FormulaVersion per context, ``supplier_type → context``
    # mappings, and the seeded FX rate (``fx_cny_rub``). DB-only,
    # idempotent via deterministic ``uuid5`` keys. Depends on ``pricing``
    # (system variables ``purchase_price_*`` / ``fx_cny_rub`` must exist).
    Step(
        "pricing_config",
        seed_pricing_config,
        db_only=True,
        deps=("pricing",),
    ),
    Step("brands", seed_brands, db_only=False, deps=("admin",)),
    Step("categories", seed_categories, db_only=False, deps=("admin",)),
    Step("attributes", seed_attributes, db_only=False, deps=("admin", "categories")),
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


def _parse_steps(raw: str | None, *, no_deps: bool = False) -> list[Step]:
    if not raw:
        return list(STEPS)
    requested = {s.strip() for s in raw.split(",") if s.strip()}
    unknown = requested - set(STEP_NAMES)
    if unknown:
        raise SystemExit(
            f"Unknown step(s): {', '.join(sorted(unknown))}. "
            f"Valid: {', '.join(STEP_NAMES)}"
        )

    if no_deps:
        # Explicit opt-out: run exactly what was requested. The caller
        # is responsible for ensuring referential integrity (e.g. admin
        # user already exists on the target server).
        return [s for s in STEPS if s.name in requested]

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
            f"(required by {', '.join(sorted(requested))}). "
            f"Use --no-deps to skip."
        )

    return [s for s in STEPS if s.name in closure]


def main() -> None:
    defaults = _admin_defaults()

    parser = argparse.ArgumentParser(description="Seed the Loyality backend.")
    parser.add_argument(
        "--step",
        help=f"Comma-separated subset of steps to run. Default: all. Valid: {', '.join(STEP_NAMES)}",
    )
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="Skip auto-inclusion of transitive deps — run only the explicitly requested steps.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--login", default=defaults["email"])
    parser.add_argument("--password", default=defaults["password"])
    args = parser.parse_args()

    steps = _parse_steps(args.step, no_deps=args.no_deps)
    ctx = SeedContext(base_url=args.base_url, login=args.login, password=args.password)
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
