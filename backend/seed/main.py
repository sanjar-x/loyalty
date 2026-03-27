"""Seed the local API with reference data.

Runs steps in dependency order:
  brands → categories → attributes → products
Each step is idempotent (conflicts are skipped, safe to re-run).

Usage:
    uv run python -m seed.main
"""

import argparse
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from seed.attributes.create_attributes import seed_attributes
from seed.brands.create_brands import seed_brands
from seed.categories.create_categories import seed_categories
from seed.products.create_products import seed_products

API_PREFIX = "/api/v1"
DEFAULT_LOGIN = "sanjar68x@gmail.com"
DEFAULT_PASSWORD = "Admin123!"


@dataclass
class SeedContext:
    """Shared context passed to every seed step."""

    client: httpx.Client
    token: str
    api_prefix: str


STEPS: dict[str, tuple[str, Callable[[SeedContext], None]]] = {
    "brands": ("Brands (34)", seed_brands),
    "categories": ("Categories (35)", seed_categories),
    "attributes": ("Attrs + Values + Templates + Bindings", seed_attributes),
    "products": ("Products (10) + SKUs + Attrs", seed_products),
}


def login(client: httpx.Client, api_prefix: str) -> str:
    """Authenticate and return the access token."""
    print(f"  Logging in as {DEFAULT_LOGIN} ...")
    r = client.post(
        f"{api_prefix}/auth/login",
        json={"login": DEFAULT_LOGIN, "password": DEFAULT_PASSWORD},
    )
    if r.status_code != 200:
        print(f"  Login failed: {r.status_code} {r.text[:120]}")
        sys.exit(1)
    token = r.json()["accessToken"]
    print("  OK\n")
    return token


def run_steps(ctx: SeedContext, steps: list[str]) -> None:
    """Execute seed steps sequentially with timing."""
    total_start = time.perf_counter()

    for i, name in enumerate(steps, 1):
        label, fn = STEPS[name]
        print(f"[{i}/{len(steps)}] {label}")
        print("-" * 40)
        start = time.perf_counter()
        fn(ctx)
        elapsed = time.perf_counter() - start
        print(f"  ({elapsed:.1f}s)\n")

    total = time.perf_counter() - total_start
    print(f"Total: {total:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed local API with reference data")
    parser.add_argument(
        "--base-url", default="https://backend-production-43b6.up.railway.app"
    )
    parser.add_argument(
        "--step",
        help=f"Comma-separated steps. Available: {', '.join(STEPS)}",
    )
    args = parser.parse_args()

    steps = args.step.split(",") if args.step else list(STEPS.keys())
    for s in steps:
        if s not in STEPS:
            print(f"Unknown step '{s}'. Available: {', '.join(STEPS)}")
            sys.exit(1)

    print(f"=== Seed -> {args.base_url} ===\n")

    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        token = login(client, API_PREFIX)
        ctx = SeedContext(client=client, token=token, api_prefix=API_PREFIX)
        run_steps(ctx, steps)

    print("=== Done ===")


if __name__ == "__main__":
    main()
