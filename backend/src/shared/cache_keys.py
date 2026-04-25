"""Cross-module cache invalidation primitives.

Shared kernel — must not import any business module.

Currently exposes the storefront product generation counter, used by
the catalog storefront caches (PLP, PDP, search) and bumped by any
module whose data participates in the storefront projection (catalog
itself, supplier — through ``supplier.type`` exposure).
"""

from src.shared.interfaces.cache import ICacheService

STOREFRONT_PRODUCT_GENERATION_KEY = "catalog:storefront:product:generation"
"""Monotonically-increasing generation counter for product storefront caches.

Bumped on any mutation that affects the storefront projection of a
product (catalog product update, supplier-type change, supplier
deactivation). Participates in PLP/search query hashes and the PDP
cache key, so a single ``INCR`` invalidates every cache entry across
the storefront slice without scanning Redis."""


async def read_storefront_product_generation(cache: ICacheService) -> int:
    """Read the current storefront product generation (0 when absent).

    Falls back to ``0`` on backend failure or first call so cache
    keys remain deterministic; the next ``bump`` will move it to
    ``1`` and naturally invalidate any pre-existing entries.
    """
    try:
        raw = await cache.get(STOREFRONT_PRODUCT_GENERATION_KEY)
    except Exception:
        return 0
    if not raw:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


async def bump_storefront_product_generation(cache: ICacheService) -> int | None:
    """Atomically increment the storefront product generation counter."""
    return await cache.increment(STOREFRONT_PRODUCT_GENERATION_KEY)
