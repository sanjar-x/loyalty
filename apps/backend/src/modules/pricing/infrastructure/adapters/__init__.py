"""Pricing anti-corruption adapters (ADR-005).

Whitelisted in ``tests/architecture/test_boundaries.py`` to read SKU
purchase price from catalog and write computed selling price back. The
pricing domain layer never touches catalog ORM directly — it consumes
:class:`SkuPricingInputs` / :class:`SkuPricingScopeSnapshot` DTOs and
writes via :class:`SkuPricingApplyRequest` / :class:`SkuPricingFailureRequest`.
"""
