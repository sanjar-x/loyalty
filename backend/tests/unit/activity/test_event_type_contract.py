"""Regression guard for the activity ``event_type`` string contract.

Bug history
-----------
An earlier iteration of :mod:`src.modules.activity.infrastructure.history_reader`
hard-coded the filter value as ``"product_view"`` while the Redis tracker
persists events as ``"product_viewed"`` (domain enum
:class:`ActivityEventType.PRODUCT_VIEWED`).  The mismatch silently broke the
warm "Для вас" personalization branch for every user — category affinities
returned empty, and the feed always fell back to the cold-start path.

These tests pin the canonical string so any future rename requires an
explicit domain-level change plus an intentional update here, catching the
drift at import time.
"""

from __future__ import annotations

from src.modules.activity.domain.value_objects import ActivityEventType
from src.modules.activity.infrastructure import history_reader, tasks


def test_product_viewed_canonical_value() -> None:
    assert ActivityEventType.PRODUCT_VIEWED.value == "product_viewed"


def test_history_reader_uses_enum_value() -> None:
    assert ActivityEventType.PRODUCT_VIEWED.value == history_reader._EVENT_PRODUCT_VIEW


def test_popularity_and_coview_sql_reference_canonical_event_type() -> None:
    # Both background jobs filter raw events by the canonical string;
    # a rename without touching the SQL would zero-out popularity and
    # "also-viewed" results without any test failure, so pin it here.
    from pathlib import Path

    source = Path(tasks.__file__).read_text(encoding="utf-8")
    assert source.count("'product_viewed'") >= 2
