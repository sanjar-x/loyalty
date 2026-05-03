"""Unit tests for the FavoriteList aggregate — invariants and idempotency."""

import uuid

import pytest

from src.modules.favorites.domain.entities import (
    DEFAULT_LIST_NAME,
    MAX_LIST_NAME_LENGTH,
    FavoriteList,
)
from src.modules.favorites.domain.events import (
    FavoriteItemAddedEvent,
    FavoriteItemRemovedEvent,
    FavoriteListCreatedEvent,
    FavoriteListDeletedEvent,
    FavoriteListRenamedEvent,
)
from src.modules.favorites.domain.exceptions import DefaultListImmutableError
from src.modules.favorites.domain.value_objects import FavoriteTargetType


@pytest.mark.unit
class TestCreateDefault:
    def test_emits_created_event(self) -> None:
        identity_id = uuid.uuid4()
        favorite_list = FavoriteList.create_default(identity_id)
        assert favorite_list.is_default is True
        assert favorite_list.name == DEFAULT_LIST_NAME
        assert favorite_list.identity_id == identity_id
        events = favorite_list.domain_events
        assert len(events) == 1
        assert isinstance(events[0], FavoriteListCreatedEvent)
        assert events[0].is_default is True


@pytest.mark.unit
class TestCreateCustom:
    def test_trims_name(self) -> None:
        favorite_list = FavoriteList.create(
            identity_id=uuid.uuid4(),
            name="  Wishlist  ",
        )
        assert favorite_list.name == "Wishlist"
        assert favorite_list.is_default is False

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            FavoriteList.create(identity_id=uuid.uuid4(), name="   ")

    def test_rejects_too_long_name(self) -> None:
        with pytest.raises(ValueError, match=str(MAX_LIST_NAME_LENGTH)):
            FavoriteList.create(
                identity_id=uuid.uuid4(),
                name="x" * (MAX_LIST_NAME_LENGTH + 1),
            )


@pytest.mark.unit
class TestRename:
    def test_rename_emits_event(self) -> None:
        favorite_list = FavoriteList.create(identity_id=uuid.uuid4(), name="Old")
        favorite_list.clear_domain_events()
        favorite_list.rename("New")
        assert favorite_list.name == "New"
        events = favorite_list.domain_events
        assert len(events) == 1
        assert isinstance(events[0], FavoriteListRenamedEvent)
        assert events[0].new_name == "New"

    def test_rename_to_same_name_is_noop(self) -> None:
        favorite_list = FavoriteList.create(identity_id=uuid.uuid4(), name="Wishlist")
        favorite_list.clear_domain_events()
        favorite_list.rename("Wishlist")
        assert favorite_list.domain_events == []

    def test_default_cannot_be_renamed(self) -> None:
        favorite_list = FavoriteList.create_default(uuid.uuid4())
        with pytest.raises(DefaultListImmutableError):
            favorite_list.rename("Other")


@pytest.mark.unit
class TestMarkDeleted:
    def test_emits_deleted_event(self) -> None:
        favorite_list = FavoriteList.create(identity_id=uuid.uuid4(), name="Tmp")
        favorite_list.clear_domain_events()
        favorite_list.mark_deleted()
        events = favorite_list.domain_events
        assert len(events) == 1
        assert isinstance(events[0], FavoriteListDeletedEvent)

    def test_default_cannot_be_deleted(self) -> None:
        favorite_list = FavoriteList.create_default(uuid.uuid4())
        with pytest.raises(DefaultListImmutableError):
            favorite_list.mark_deleted()


@pytest.mark.unit
class TestAddItem:
    def test_adds_new_item_and_emits_event(self) -> None:
        favorite_list = FavoriteList.create_default(uuid.uuid4())
        favorite_list.clear_domain_events()
        target_id = uuid.uuid4()
        item = favorite_list.add_item(
            target_type=FavoriteTargetType.PRODUCT,
            target_id=target_id,
        )
        assert item is not None
        assert item.target_id == target_id
        assert len(favorite_list.items) == 1
        events = favorite_list.domain_events
        assert len(events) == 1
        assert isinstance(events[0], FavoriteItemAddedEvent)

    def test_idempotent_on_duplicate(self) -> None:
        favorite_list = FavoriteList.create_default(uuid.uuid4())
        target_id = uuid.uuid4()
        favorite_list.add_item(
            target_type=FavoriteTargetType.PRODUCT, target_id=target_id
        )
        favorite_list.clear_domain_events()
        again = favorite_list.add_item(
            target_type=FavoriteTargetType.PRODUCT, target_id=target_id
        )
        assert again is None
        assert len(favorite_list.items) == 1
        assert favorite_list.domain_events == []

    def test_different_target_types_can_share_uuid(self) -> None:
        favorite_list = FavoriteList.create_default(uuid.uuid4())
        target_id = uuid.uuid4()
        favorite_list.add_item(
            target_type=FavoriteTargetType.PRODUCT, target_id=target_id
        )
        favorite_list.add_item(
            target_type=FavoriteTargetType.BRAND, target_id=target_id
        )
        assert len(favorite_list.items) == 2


@pytest.mark.unit
class TestRemoveItem:
    def test_removes_existing_and_emits_event(self) -> None:
        favorite_list = FavoriteList.create_default(uuid.uuid4())
        target_id = uuid.uuid4()
        favorite_list.add_item(
            target_type=FavoriteTargetType.BRAND, target_id=target_id
        )
        favorite_list.clear_domain_events()
        removed = favorite_list.remove_item(
            target_type=FavoriteTargetType.BRAND, target_id=target_id
        )
        assert removed is True
        assert favorite_list.items == []
        events = favorite_list.domain_events
        assert len(events) == 1
        assert isinstance(events[0], FavoriteItemRemovedEvent)

    def test_idempotent_when_absent(self) -> None:
        favorite_list = FavoriteList.create_default(uuid.uuid4())
        favorite_list.clear_domain_events()
        removed = favorite_list.remove_item(
            target_type=FavoriteTargetType.PRODUCT,
            target_id=uuid.uuid4(),
        )
        assert removed is False
        assert favorite_list.domain_events == []
