"""Unit tests for ``_coerce_grams`` — pure helper inside PricingWeightAdapter.

The adapter's SQL paths are covered by integration tests (``test_pricing_weight_adapter.py``).
This file isolates the input-shape normalisation that decides whether a stored
weight value survives or falls back to the system default.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.logistics.infrastructure.adapters.pricing_weight_adapter import (
    _coerce_grams,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("450", 450),
        ("450.0", 450),
        (450, 450),
        (450.0, 450),
        (Decimal("450"), 450),
        (Decimal("450.7"), 450),  # truncated to int (we store integer grams)
    ],
)
def test_coerce_grams_accepts_positive_numbers(raw: object, expected: int) -> None:
    assert _coerce_grams(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "not-a-number", object(), [], {}])
def test_coerce_grams_returns_none_for_garbage(raw: object) -> None:
    assert _coerce_grams(raw) is None


@pytest.mark.parametrize("raw", [0, "0", Decimal("0"), -1, "-50", Decimal("-100")])
def test_coerce_grams_rejects_non_positive(raw: object) -> None:
    """Zero / negative weight is never a valid Parcel — must fall back to default."""
    assert _coerce_grams(raw) is None
