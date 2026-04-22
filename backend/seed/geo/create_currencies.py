"""Backward-compatible shim — seed logic moved to :mod:`seed.geo.create_geo`.

The ``geo`` step now orchestrates languages, currencies, and Russia data
through the admin HTTP API (see :mod:`seed.geo.create_geo`).
"""

from seed.geo.create_geo import seed_geo

__all__ = ["seed_geo"]
