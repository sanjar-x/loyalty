# tests/unit/modules/catalog/domain/test_attribute_value.py
"""Tests for AttributeValue domain entity, events, and exceptions."""

import uuid

import pytest

from src.modules.catalog.domain.entities import AttributeValue
from src.modules.catalog.domain.events import (
    AttributeValueAddedEvent,
    AttributeValueDeletedEvent,
    AttributeValueUpdatedEvent,
)
from src.modules.catalog.domain.exceptions import (
    AttributeNotDictionaryError,
    AttributeValueCodeConflictError,
    AttributeValueNotFoundError,
    AttributeValueSlugConflictError,
)


def _make_attr_id() -> uuid.UUID:
    return uuid.uuid4()


def _make_value(**overrides) -> AttributeValue:
    defaults = {
        "attribute_id": _make_attr_id(),
        "code": "red",
        "slug": "red",
        "value_i18n": {"en": "Red", "ru": "Красный"},
    }
    defaults.update(overrides)
    return AttributeValue.create(**defaults)


# ---------------------------------------------------------------------------
# AttributeValue entity -- creation
# ---------------------------------------------------------------------------


class TestAttributeValueCreate:
    def test_create_sets_all_fields(self):
        attr_id = _make_attr_id()
        val = AttributeValue.create(
            attribute_id=attr_id,
            code="red",
            slug="red",
            value_i18n={"en": "Red", "ru": "Красный"},
            search_aliases=["scarlet", "crimson"],
            meta_data={"hex": "#FF0000"},
            value_group="Warm tones",
            sort_order=1,
        )
        assert val.attribute_id == attr_id
        assert val.code == "red"
        assert val.slug == "red"
        assert val.value_i18n == {"en": "Red", "ru": "Красный"}
        assert val.search_aliases == ["scarlet", "crimson"]
        assert val.meta_data == {"hex": "#FF0000"}
        assert val.value_group == "Warm tones"
        assert val.sort_order == 1
        assert isinstance(val.id, uuid.UUID)

    def test_create_with_defaults(self):
        val = _make_value()
        assert val.search_aliases == []
        assert val.meta_data == {}
        assert val.value_group is None
        assert val.sort_order == 0

    def test_create_with_custom_id(self):
        custom_id = uuid.uuid4()
        val = _make_value(value_id=custom_id)
        assert val.id == custom_id

    def test_create_raises_on_empty_value_i18n(self):
        with pytest.raises(ValueError, match="value_i18n must contain at least one language"):
            _make_value(value_i18n={})


# ---------------------------------------------------------------------------
# AttributeValue entity -- update
# ---------------------------------------------------------------------------


class TestAttributeValueUpdate:
    def test_update_value_i18n(self):
        val = _make_value()
        val.update(value_i18n={"en": "Scarlet", "uz": "Qizil"})
        assert val.value_i18n == {"en": "Scarlet", "uz": "Qizil"}

    def test_update_search_aliases(self):
        val = _make_value()
        val.update(search_aliases=["cherry", "ruby"])
        assert val.search_aliases == ["cherry", "ruby"]

    def test_update_meta_data(self):
        val = _make_value()
        val.update(meta_data={"hex": "#CC0000", "pantone": "186 C"})
        assert val.meta_data == {"hex": "#CC0000", "pantone": "186 C"}

    def test_update_value_group_set(self):
        val = _make_value()
        val.update(value_group="Cool tones")
        assert val.value_group == "Cool tones"

    def test_update_value_group_clear(self):
        val = _make_value(value_group="Warm tones")
        val.update(value_group=None)
        assert val.value_group is None

    def test_update_sort_order(self):
        val = _make_value()
        val.update(sort_order=42)
        assert val.sort_order == 42

    def test_update_with_no_args_keeps_current(self):
        val = _make_value(
            value_i18n={"en": "Red"},
            search_aliases=["scarlet"],
            meta_data={"hex": "#FF0000"},
            value_group="Warm",
            sort_order=5,
        )
        val.update()  # all defaults (None or sentinel)
        assert val.value_i18n == {"en": "Red"}
        assert val.search_aliases == ["scarlet"]
        assert val.meta_data == {"hex": "#FF0000"}
        assert val.value_group == "Warm"
        assert val.sort_order == 5

    def test_update_raises_on_empty_value_i18n(self):
        val = _make_value()
        with pytest.raises(ValueError, match="value_i18n must contain at least one language"):
            val.update(value_i18n={})

    def test_code_and_slug_not_in_update_signature(self):
        val = _make_value()
        with pytest.raises(TypeError):
            val.update(code="new_code")  # type: ignore[call-arg]
        with pytest.raises(TypeError):
            val.update(slug="new-slug")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# AttributeValue domain events
# ---------------------------------------------------------------------------


class TestAttributeValueAddedEvent:
    def test_raises_when_attribute_id_is_none(self):
        with pytest.raises(ValueError, match="attribute_id is required"):
            AttributeValueAddedEvent(attribute_id=None, value_id=uuid.uuid4(), code="red")

    def test_raises_when_value_id_is_none(self):
        with pytest.raises(ValueError, match="value_id is required"):
            AttributeValueAddedEvent(attribute_id=uuid.uuid4(), value_id=None, code="red")

    def test_auto_sets_aggregate_id_from_attribute_id(self):
        attr_id = uuid.uuid4()
        event = AttributeValueAddedEvent(attribute_id=attr_id, value_id=uuid.uuid4(), code="red")
        assert event.aggregate_id == str(attr_id)

    def test_fields_populated(self):
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        event = AttributeValueAddedEvent(attribute_id=attr_id, value_id=val_id, code="blue")
        assert event.aggregate_type == "Attribute"
        assert event.event_type == "AttributeValueAddedEvent"
        assert event.code == "blue"
        assert event.value_id == val_id


class TestAttributeValueUpdatedEvent:
    def test_raises_when_attribute_id_is_none(self):
        with pytest.raises(ValueError, match="attribute_id is required"):
            AttributeValueUpdatedEvent(attribute_id=None, value_id=uuid.uuid4())

    def test_raises_when_value_id_is_none(self):
        with pytest.raises(ValueError, match="value_id is required"):
            AttributeValueUpdatedEvent(attribute_id=uuid.uuid4(), value_id=None)

    def test_auto_sets_aggregate_id(self):
        attr_id = uuid.uuid4()
        event = AttributeValueUpdatedEvent(attribute_id=attr_id, value_id=uuid.uuid4())
        assert event.aggregate_id == str(attr_id)


class TestAttributeValueDeletedEvent:
    def test_raises_when_attribute_id_is_none(self):
        with pytest.raises(ValueError, match="attribute_id is required"):
            AttributeValueDeletedEvent(attribute_id=None, value_id=uuid.uuid4(), code="red")

    def test_raises_when_value_id_is_none(self):
        with pytest.raises(ValueError, match="value_id is required"):
            AttributeValueDeletedEvent(attribute_id=uuid.uuid4(), value_id=None, code="red")

    def test_fields_populated(self):
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        event = AttributeValueDeletedEvent(attribute_id=attr_id, value_id=val_id, code="red")
        assert event.aggregate_type == "Attribute"
        assert event.event_type == "AttributeValueDeletedEvent"
        assert event.code == "red"


# ---------------------------------------------------------------------------
# AttributeValue domain exceptions
# ---------------------------------------------------------------------------


class TestAttributeValueExceptions:
    def test_not_found_error(self):
        vid = uuid.uuid4()
        error = AttributeValueNotFoundError(value_id=vid)
        assert error.status_code == 404
        assert error.error_code == "ATTRIBUTE_VALUE_NOT_FOUND"
        assert str(vid) in error.message

    def test_code_conflict_error(self):
        attr_id = uuid.uuid4()
        error = AttributeValueCodeConflictError(code="red", attribute_id=attr_id)
        assert error.status_code == 409
        assert error.error_code == "ATTRIBUTE_VALUE_CODE_CONFLICT"
        assert "red" in error.message
        assert error.details is not None
        assert error.details["attribute_id"] == str(attr_id)

    def test_slug_conflict_error(self):
        attr_id = uuid.uuid4()
        error = AttributeValueSlugConflictError(slug="red", attribute_id=attr_id)
        assert error.status_code == 409
        assert error.error_code == "ATTRIBUTE_VALUE_SLUG_CONFLICT"

    def test_not_dictionary_error(self):
        attr_id = uuid.uuid4()
        error = AttributeNotDictionaryError(attribute_id=attr_id)
        assert error.status_code == 422
        assert error.error_code == "ATTRIBUTE_NOT_DICTIONARY"
        assert "dictionary" in error.message.lower()
