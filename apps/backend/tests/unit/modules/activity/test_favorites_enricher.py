"""Unit tests for the favorites → activity enricher (T-3 / D3.2)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.modules.activity.application.consumers.favorites_events import (
    FavoritesActivityEnricher,
)
from src.shared.interfaces.activity import IActivityTracker

pytestmark = pytest.mark.unit


class _StubTracker(IActivityTracker):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def track_product_view(
        self, **kwargs: Any
    ) -> None:  # pragma: no cover — unused
        self.calls.append({"kind": "product_view", **kwargs})

    async def track_product_list_view(
        self, **kwargs: Any
    ) -> None:  # pragma: no cover — unused
        self.calls.append({"kind": "list_view", **kwargs})

    async def track_search(self, **kwargs: Any) -> None:  # pragma: no cover — unused
        self.calls.append({"kind": "search", **kwargs})

    async def track_favorite_added(
        self,
        *,
        product_id: uuid.UUID,
        actor_id: uuid.UUID,
        list_id: uuid.UUID | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.calls.append({
            "kind": "favorite_added",
            "product_id": product_id,
            "actor_id": actor_id,
            "list_id": list_id,
            "extra": extra,
        })


class _NullLogger:
    def bind(self, **_: Any) -> _NullLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def critical(self, *_: Any, **__: Any) -> None: ...
    def debug(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


def _build() -> tuple[FavoritesActivityEnricher, _StubTracker]:
    tracker = _StubTracker()
    consumer = FavoritesActivityEnricher(
        tracker=tracker,
        logger=_NullLogger(),
    )
    return consumer, tracker


async def test_product_target_invokes_tracker() -> None:
    consumer, tracker = _build()
    identity_id = uuid.uuid4()
    product_id = uuid.uuid4()
    list_id = uuid.uuid4()

    await consumer.on_favorite_item_added({
        "list_id": str(list_id),
        "identity_id": str(identity_id),
        "target_type": "product",
        "target_id": str(product_id),
    })

    assert len(tracker.calls) == 1
    call = tracker.calls[0]
    assert call["kind"] == "favorite_added"
    assert call["product_id"] == product_id
    assert call["actor_id"] == identity_id
    assert call["list_id"] == list_id


async def test_brand_target_is_skipped() -> None:
    """Brand favorites: not a product co-view signal."""
    consumer, tracker = _build()
    await consumer.on_favorite_item_added({
        "list_id": str(uuid.uuid4()),
        "identity_id": str(uuid.uuid4()),
        "target_type": "brand",
        "target_id": str(uuid.uuid4()),
    })
    assert tracker.calls == []


async def test_missing_identity_id_is_skipped() -> None:
    consumer, tracker = _build()
    await consumer.on_favorite_item_added({
        "list_id": str(uuid.uuid4()),
        "target_type": "product",
        "target_id": str(uuid.uuid4()),
    })
    assert tracker.calls == []


async def test_missing_target_id_is_skipped() -> None:
    consumer, tracker = _build()
    await consumer.on_favorite_item_added({
        "list_id": str(uuid.uuid4()),
        "identity_id": str(uuid.uuid4()),
        "target_type": "product",
    })
    assert tracker.calls == []


async def test_bad_uuid_is_skipped() -> None:
    consumer, tracker = _build()
    await consumer.on_favorite_item_added({
        "list_id": str(uuid.uuid4()),
        "identity_id": "not-a-uuid",
        "target_type": "product",
        "target_id": str(uuid.uuid4()),
    })
    assert tracker.calls == []


async def test_null_list_id_passes_through_as_none() -> None:
    consumer, tracker = _build()
    await consumer.on_favorite_item_added({
        "list_id": None,
        "identity_id": str(uuid.uuid4()),
        "target_type": "product",
        "target_id": str(uuid.uuid4()),
    })
    assert len(tracker.calls) == 1
    assert tracker.calls[0]["list_id"] is None
