"""Unit tests for the cancellation-reasons meta taxonomy (C5.2)."""

from __future__ import annotations

import pytest

from src.modules.order.domain.value_objects import (
    CancellationCategory,
    CancellationReason,
    category_of,
)

pytestmark = pytest.mark.unit


def test_every_reason_is_categorised() -> None:
    """``category_of`` must cover every CancellationReason — the
    front-end ``ForceCancelModal`` dropdown groups by category, so
    a missing mapping would silently drop the reason from the UI."""
    for reason in CancellationReason:
        category_of(reason)  # raises KeyError if any reason is missing


def test_every_category_has_at_least_one_reason() -> None:
    """The grouped ``_meta`` response is built by walking every
    CancellationCategory; an empty group would surface as an empty
    section in the dropdown."""
    grouped: dict[CancellationCategory, list[CancellationReason]] = {
        cat: [] for cat in CancellationCategory
    }
    for reason in CancellationReason:
        grouped[category_of(reason)].append(reason)
    for cat, reasons in grouped.items():
        assert reasons, f"Category {cat.value!r} has no reasons"


def test_reason_count_matches_brief() -> None:
    """The Sprint 2 brief documented 19 reasons in 4 groups — lock
    the count so any new reason addition forces a doc / UI update."""
    assert len(list(CancellationReason)) == 19
    assert len(list(CancellationCategory)) == 4
