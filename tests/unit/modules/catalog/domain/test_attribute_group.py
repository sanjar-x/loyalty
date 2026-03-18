# tests/unit/modules/catalog/domain/test_attribute_group.py
"""Tests for AttributeGroup domain entity and related events/exceptions."""

import uuid

import pytest

from src.modules.catalog.domain.entities import GENERAL_GROUP_CODE, AttributeGroup
from src.modules.catalog.domain.events import (
    AttributeGroupCreatedEvent,
    AttributeGroupDeletedEvent,
    AttributeGroupUpdatedEvent,
)
from src.modules.catalog.domain.exceptions import (
    AttributeGroupCannotDeleteGeneralError,
    AttributeGroupCodeConflictError,
    AttributeGroupHasAttributesError,
    AttributeGroupNotFoundError,
)
from tests.factories.catalog_mothers import AttributeGroupMothers

# ---------------------------------------------------------------------------
# AttributeGroup entity — creation
# ---------------------------------------------------------------------------


class TestAttributeGroupCreate:
    def test_create_sets_all_fields(self):
        group = AttributeGroup.create(
            code="physical",
            name_i18n={"en": "Physical", "ru": "Физические"},
            sort_order=1,
        )
        assert group.code == "physical"
        assert group.name_i18n == {"en": "Physical", "ru": "Физические"}
        assert group.sort_order == 1
        assert isinstance(group.id, uuid.UUID)

    def test_create_with_pre_generated_id(self):
        custom_id = uuid.uuid4()
        group = AttributeGroup.create(
            code="test",
            name_i18n={"en": "Test"},
            group_id=custom_id,
        )
        assert group.id == custom_id

    def test_create_defaults_sort_order_to_zero(self):
        group = AttributeGroup.create(code="test", name_i18n={"en": "Test"})
        assert group.sort_order == 0

    def test_create_raises_on_empty_name_i18n(self):
        with pytest.raises(ValueError, match="name_i18n must contain at least one language entry"):
            AttributeGroup.create(code="test", name_i18n={})


# ---------------------------------------------------------------------------
# AttributeGroup entity — update
# ---------------------------------------------------------------------------


class TestAttributeGroupUpdate:
    def test_update_name_i18n(self):
        group = AttributeGroupMothers.physical()
        group.update(name_i18n={"en": "Updated Name", "uz": "Yangilangan"})
        assert group.name_i18n == {"en": "Updated Name", "uz": "Yangilangan"}

    def test_update_sort_order(self):
        group = AttributeGroupMothers.physical()
        group.update(sort_order=99)
        assert group.sort_order == 99

    def test_update_both_fields(self):
        group = AttributeGroupMothers.physical()
        group.update(name_i18n={"en": "New"}, sort_order=42)
        assert group.name_i18n == {"en": "New"}
        assert group.sort_order == 42

    def test_update_with_none_keeps_current(self):
        group = AttributeGroupMothers.physical()
        original_name = group.name_i18n.copy()
        original_sort = group.sort_order
        group.update()  # no args
        assert group.name_i18n == original_name
        assert group.sort_order == original_sort

    def test_update_raises_on_empty_name_i18n(self):
        group = AttributeGroupMothers.physical()
        with pytest.raises(ValueError, match="name_i18n must contain at least one language entry"):
            group.update(name_i18n={})


# ---------------------------------------------------------------------------
# AttributeGroup entity — is_general property
# ---------------------------------------------------------------------------


class TestAttributeGroupIsGeneral:
    def test_general_group_returns_true(self):
        group = AttributeGroupMothers.general()
        assert group.is_general is True

    def test_non_general_group_returns_false(self):
        group = AttributeGroupMothers.physical()
        assert group.is_general is False

    def test_general_group_code_constant(self):
        assert GENERAL_GROUP_CODE == "general"


# ---------------------------------------------------------------------------
# AttributeGroup domain events
# ---------------------------------------------------------------------------


class TestAttributeGroupCreatedEvent:
    def test_raises_when_group_id_is_none(self):
        with pytest.raises(ValueError, match="group_id is required"):
            AttributeGroupCreatedEvent(group_id=None, code="test")

    def test_auto_sets_aggregate_id(self):
        group_id = uuid.uuid4()
        event = AttributeGroupCreatedEvent(group_id=group_id, code="test")
        assert event.aggregate_id == str(group_id)

    def test_fields_populated(self):
        group_id = uuid.uuid4()
        event = AttributeGroupCreatedEvent(group_id=group_id, code="physical")
        assert event.aggregate_type == "AttributeGroup"
        assert event.event_type == "AttributeGroupCreatedEvent"
        assert event.code == "physical"


class TestAttributeGroupUpdatedEvent:
    def test_raises_when_group_id_is_none(self):
        with pytest.raises(ValueError, match="group_id is required"):
            AttributeGroupUpdatedEvent(group_id=None)

    def test_auto_sets_aggregate_id(self):
        group_id = uuid.uuid4()
        event = AttributeGroupUpdatedEvent(group_id=group_id)
        assert event.aggregate_id == str(group_id)

    def test_fields_populated(self):
        event = AttributeGroupUpdatedEvent(group_id=uuid.uuid4())
        assert event.aggregate_type == "AttributeGroup"
        assert event.event_type == "AttributeGroupUpdatedEvent"


class TestAttributeGroupDeletedEvent:
    def test_raises_when_group_id_is_none(self):
        with pytest.raises(ValueError, match="group_id is required"):
            AttributeGroupDeletedEvent(group_id=None, code="test")

    def test_auto_sets_aggregate_id(self):
        group_id = uuid.uuid4()
        event = AttributeGroupDeletedEvent(group_id=group_id, code="test")
        assert event.aggregate_id == str(group_id)

    def test_fields_populated(self):
        group_id = uuid.uuid4()
        event = AttributeGroupDeletedEvent(group_id=group_id, code="physical")
        assert event.aggregate_type == "AttributeGroup"
        assert event.event_type == "AttributeGroupDeletedEvent"
        assert event.code == "physical"


# ---------------------------------------------------------------------------
# AttributeGroup domain exceptions
# ---------------------------------------------------------------------------


class TestAttributeGroupExceptions:
    def test_not_found_error(self):
        group_id = uuid.uuid4()
        error = AttributeGroupNotFoundError(group_id=group_id)
        assert error.status_code == 404
        assert error.error_code == "ATTRIBUTE_GROUP_NOT_FOUND"
        assert str(group_id) in error.message

    def test_code_conflict_error(self):
        error = AttributeGroupCodeConflictError(code="physical")
        assert error.status_code == 409
        assert error.error_code == "ATTRIBUTE_GROUP_CODE_CONFLICT"
        assert "physical" in error.message

    def test_has_attributes_error(self):
        group_id = uuid.uuid4()
        error = AttributeGroupHasAttributesError(group_id=group_id)
        assert error.status_code == 409
        assert error.error_code == "ATTRIBUTE_GROUP_HAS_ATTRIBUTES"

    def test_cannot_delete_general_error(self):
        error = AttributeGroupCannotDeleteGeneralError()
        assert error.status_code == 422
        assert error.error_code == "ATTRIBUTE_GROUP_CANNOT_DELETE_GENERAL"
        assert error.details["code"] == "general"


# ---------------------------------------------------------------------------
# Object Mothers validation
# ---------------------------------------------------------------------------


class TestAttributeGroupMothers:
    def test_general_mother(self):
        group = AttributeGroupMothers.general()
        assert group.code == "general"
        assert group.is_general is True
        assert "en" in group.name_i18n

    def test_physical_mother(self):
        group = AttributeGroupMothers.physical()
        assert group.code.startswith("physical-")
        assert group.is_general is False

    def test_technical_mother(self):
        group = AttributeGroupMothers.technical()
        assert group.code.startswith("technical-")
        assert group.sort_order == 2

    def test_custom_mother(self):
        group = AttributeGroupMothers.custom(
            code="my-group",
            name_i18n={"en": "My Group"},
            sort_order=5,
        )
        assert group.code == "my-group"
        assert group.sort_order == 5
