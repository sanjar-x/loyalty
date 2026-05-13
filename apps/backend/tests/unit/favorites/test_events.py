"""Unit tests for favorites domain event invariants."""

import uuid

import pytest

from src.modules.favorites.domain.events import (
    FavoriteItemAddedEvent,
    FavoriteListCreatedEvent,
)


@pytest.mark.unit
class TestFavoriteEventValidation:
    def test_required_fields_enforced(self) -> None:
        with pytest.raises(ValueError, match="list_id is required"):
            FavoriteListCreatedEvent(identity_id=uuid.uuid4())

    def test_aggregate_id_auto_derived(self) -> None:
        list_id = uuid.uuid4()
        event = FavoriteListCreatedEvent(
            list_id=list_id,
            identity_id=uuid.uuid4(),
            name="x",
            is_default=True,
        )
        assert event.aggregate_id == str(list_id)
        assert event.aggregate_type == "favorites"

    def test_item_event_carries_target(self) -> None:
        list_id = uuid.uuid4()
        target_id = uuid.uuid4()
        event = FavoriteItemAddedEvent(
            list_id=list_id,
            identity_id=uuid.uuid4(),
            target_type="product",
            target_id=target_id,
        )
        assert event.target_id == target_id
        assert event.aggregate_id == str(list_id)
