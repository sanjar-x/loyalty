# tests/unit/modules/catalog/domain/test_category_attribute_binding.py
"""Tests for CategoryAttributeBinding entity, events, exceptions, and value objects."""

import uuid

import pytest

from src.modules.catalog.domain.entities import CategoryAttributeBinding
from src.modules.catalog.domain.events import (
    AttributeBoundToCategoryEvent,
    AttributeUnboundFromCategoryEvent,
    CategoryAttributeBindingUpdatedEvent,
)
from src.modules.catalog.domain.exceptions import (
    CategoryAttributeBindingAlreadyExistsError,
    CategoryAttributeBindingNotFoundError,
)
from src.modules.catalog.domain.value_objects import RequirementLevel

# ---------------------------------------------------------------------------
# RequirementLevel enum
# ---------------------------------------------------------------------------


class TestRequirementLevel:
    def test_required_value(self):
        assert RequirementLevel.REQUIRED.value == "required"

    def test_recommended_value(self):
        assert RequirementLevel.RECOMMENDED.value == "recommended"

    def test_optional_value(self):
        assert RequirementLevel.OPTIONAL.value == "optional"


# ---------------------------------------------------------------------------
# CategoryAttributeBinding entity -- creation
# ---------------------------------------------------------------------------


class TestCategoryAttributeBindingCreate:
    def test_create_with_defaults(self):
        cat_id = uuid.uuid4()
        attr_id = uuid.uuid4()
        binding = CategoryAttributeBinding.create(
            category_id=cat_id,
            attribute_id=attr_id,
        )
        assert binding.category_id == cat_id
        assert binding.attribute_id == attr_id
        assert binding.sort_order == 0
        assert binding.requirement_level == RequirementLevel.OPTIONAL
        assert binding.flag_overrides is None
        assert binding.filter_settings is None
        assert isinstance(binding.id, uuid.UUID)

    def test_create_with_all_fields(self):
        cat_id = uuid.uuid4()
        attr_id = uuid.uuid4()
        overrides = {"is_filterable": True, "search_weight": 8}
        filters = {"filter_type": "range", "thresholds": [0, 5000, 10000]}
        binding = CategoryAttributeBinding.create(
            category_id=cat_id,
            attribute_id=attr_id,
            sort_order=5,
            requirement_level=RequirementLevel.REQUIRED,
            flag_overrides=overrides,
            filter_settings=filters,
        )
        assert binding.sort_order == 5
        assert binding.requirement_level == RequirementLevel.REQUIRED
        assert binding.flag_overrides == overrides
        assert binding.filter_settings == filters

    def test_create_with_custom_id(self):
        custom_id = uuid.uuid4()
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(),
            attribute_id=uuid.uuid4(),
            binding_id=custom_id,
        )
        assert binding.id == custom_id

    def test_create_recommended_level(self):
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(),
            attribute_id=uuid.uuid4(),
            requirement_level=RequirementLevel.RECOMMENDED,
        )
        assert binding.requirement_level == RequirementLevel.RECOMMENDED


# ---------------------------------------------------------------------------
# CategoryAttributeBinding entity -- update
# ---------------------------------------------------------------------------


class TestCategoryAttributeBindingUpdate:
    def test_update_sort_order(self):
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(), attribute_id=uuid.uuid4()
        )
        binding.update(sort_order=10)
        assert binding.sort_order == 10

    def test_update_requirement_level(self):
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(), attribute_id=uuid.uuid4()
        )
        binding.update(requirement_level=RequirementLevel.REQUIRED)
        assert binding.requirement_level == RequirementLevel.REQUIRED

    def test_update_flag_overrides_set(self):
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(), attribute_id=uuid.uuid4()
        )
        binding.update(flag_overrides={"is_filterable": True})
        assert binding.flag_overrides == {"is_filterable": True}

    def test_update_flag_overrides_clear(self):
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(),
            attribute_id=uuid.uuid4(),
            flag_overrides={"is_filterable": True},
        )
        binding.update(flag_overrides=None)
        assert binding.flag_overrides is None

    def test_update_flag_overrides_keep_with_sentinel(self):
        original = {"is_filterable": True}
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(),
            attribute_id=uuid.uuid4(),
            flag_overrides=original,
        )
        binding.update()  # flag_overrides defaults to ...
        assert binding.flag_overrides == original

    def test_update_filter_settings_set(self):
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(), attribute_id=uuid.uuid4()
        )
        settings = {"filter_type": "dropdown"}
        binding.update(filter_settings=settings)
        assert binding.filter_settings == settings

    def test_update_filter_settings_clear(self):
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(),
            attribute_id=uuid.uuid4(),
            filter_settings={"filter_type": "range"},
        )
        binding.update(filter_settings=None)
        assert binding.filter_settings is None

    def test_update_no_args_keeps_current(self):
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(),
            attribute_id=uuid.uuid4(),
            sort_order=3,
            requirement_level=RequirementLevel.RECOMMENDED,
            flag_overrides={"is_filterable": True},
            filter_settings={"filter_type": "range"},
        )
        binding.update()
        assert binding.sort_order == 3
        assert binding.requirement_level == RequirementLevel.RECOMMENDED
        assert binding.flag_overrides == {"is_filterable": True}
        assert binding.filter_settings == {"filter_type": "range"}

    def test_category_and_attribute_not_in_update(self):
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(), attribute_id=uuid.uuid4()
        )
        with pytest.raises(TypeError):
            binding.update(category_id=uuid.uuid4())  # type: ignore[call-arg]
        with pytest.raises(TypeError):
            binding.update(attribute_id=uuid.uuid4())  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# CategoryAttributeBinding is AggregateRoot
# ---------------------------------------------------------------------------


class TestCategoryAttributeBindingAggregateRoot:
    def test_can_add_domain_events(self):
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(), attribute_id=uuid.uuid4()
        )
        event = AttributeBoundToCategoryEvent(
            category_id=binding.category_id,
            attribute_id=binding.attribute_id,
            binding_id=binding.id,
        )
        binding.add_domain_event(event)
        assert len(binding.domain_events) == 1

    def test_clear_domain_events(self):
        binding = CategoryAttributeBinding.create(
            category_id=uuid.uuid4(), attribute_id=uuid.uuid4()
        )
        binding.add_domain_event(
            AttributeBoundToCategoryEvent(
                category_id=binding.category_id,
                attribute_id=binding.attribute_id,
                binding_id=binding.id,
            )
        )
        binding.clear_domain_events()
        assert len(binding.domain_events) == 0


# ---------------------------------------------------------------------------
# Domain events
# ---------------------------------------------------------------------------


class TestAttributeBoundToCategoryEvent:
    def test_raises_when_binding_id_is_none(self):
        with pytest.raises(ValueError, match="binding_id is required"):
            AttributeBoundToCategoryEvent(
                category_id=uuid.uuid4(),
                attribute_id=uuid.uuid4(),
                binding_id=None,
            )

    def test_auto_sets_aggregate_id(self):
        bid = uuid.uuid4()
        event = AttributeBoundToCategoryEvent(
            category_id=uuid.uuid4(),
            attribute_id=uuid.uuid4(),
            binding_id=bid,
        )
        assert event.aggregate_id == str(bid)

    def test_fields_populated(self):
        cat_id = uuid.uuid4()
        attr_id = uuid.uuid4()
        bid = uuid.uuid4()
        event = AttributeBoundToCategoryEvent(
            category_id=cat_id, attribute_id=attr_id, binding_id=bid
        )
        assert event.aggregate_type == "CategoryAttributeBinding"
        assert event.event_type == "AttributeBoundToCategoryEvent"
        assert event.category_id == cat_id
        assert event.attribute_id == attr_id


class TestCategoryAttributeBindingUpdatedEvent:
    def test_raises_when_binding_id_is_none(self):
        with pytest.raises(ValueError, match="binding_id is required"):
            CategoryAttributeBindingUpdatedEvent(binding_id=None)

    def test_auto_sets_aggregate_id(self):
        bid = uuid.uuid4()
        event = CategoryAttributeBindingUpdatedEvent(binding_id=bid)
        assert event.aggregate_id == str(bid)


class TestAttributeUnboundFromCategoryEvent:
    def test_raises_when_binding_id_is_none(self):
        with pytest.raises(ValueError, match="binding_id is required"):
            AttributeUnboundFromCategoryEvent(
                category_id=uuid.uuid4(),
                attribute_id=uuid.uuid4(),
                binding_id=None,
            )

    def test_fields_populated(self):
        bid = uuid.uuid4()
        event = AttributeUnboundFromCategoryEvent(
            category_id=uuid.uuid4(),
            attribute_id=uuid.uuid4(),
            binding_id=bid,
        )
        assert event.aggregate_type == "CategoryAttributeBinding"
        assert event.event_type == "AttributeUnboundFromCategoryEvent"


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class TestBindingExceptions:
    def test_not_found_error(self):
        bid = uuid.uuid4()
        error = CategoryAttributeBindingNotFoundError(binding_id=bid)
        assert error.status_code == 404
        assert error.error_code == "CATEGORY_ATTRIBUTE_BINDING_NOT_FOUND"
        assert str(bid) in error.message

    def test_already_exists_error(self):
        cat_id = uuid.uuid4()
        attr_id = uuid.uuid4()
        error = CategoryAttributeBindingAlreadyExistsError(category_id=cat_id, attribute_id=attr_id)
        assert error.status_code == 409
        assert error.error_code == "CATEGORY_ATTRIBUTE_BINDING_ALREADY_EXISTS"
        assert error.details is not None
        assert error.details["category_id"] == str(cat_id)
        assert error.details["attribute_id"] == str(attr_id)
