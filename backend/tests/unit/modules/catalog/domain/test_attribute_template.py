"""Unit tests for AttributeTemplate and TemplateAttributeBinding entities.

Covers factory methods, update logic, guarded-field __setattr__ guards,
deletion validation, and filter_settings structural validation for the
attribute template subsystem.
"""

from __future__ import annotations

import uuid

import pytest

from src.modules.catalog.domain.entities import (
    AttributeTemplate,
    TemplateAttributeBinding,
)
from src.modules.catalog.domain.exceptions import (
    AttributeTemplateHasCategoryReferencesError,
    MissingRequiredLocalesError,
)
from src.modules.catalog.domain.value_objects import RequirementLevel
from tests.factories.attribute_template_builder import (
    AttributeTemplateBuilder,
    TemplateAttributeBindingBuilder,
)


def _i18n(en: str, ru: str | None = None) -> dict[str, str]:
    return {"en": en, "ru": ru or en}


# ============================================================================
# AttributeTemplate -- create
# ============================================================================


class TestAttributeTemplateCreate:
    def test_create_valid(self):
        template = AttributeTemplateBuilder().build()
        assert isinstance(template.id, uuid.UUID)
        assert template.sort_order == 0

    def test_create_with_description(self):
        template = (
            AttributeTemplateBuilder()
            .with_description_i18n(_i18n("A template for shoes"))
            .build()
        )
        assert template.description_i18n == _i18n("A template for shoes")

    def test_create_rejects_missing_locale(self):
        with pytest.raises(MissingRequiredLocalesError):
            AttributeTemplate.create(
                code="clothing",
                name_i18n={"en": "Only English"},
            )

    def test_create_rejects_blank_i18n_values(self):
        with pytest.raises(ValueError):
            AttributeTemplate.create(
                code="clothing",
                name_i18n={"en": "", "ru": "Valid"},
            )

    def test_create_rejects_negative_sort_order(self):
        with pytest.raises(ValueError, match="sort_order must be non-negative"):
            AttributeTemplate.create(
                code="clothing",
                name_i18n=_i18n("Clothing"),
                sort_order=-1,
            )

    def test_create_custom_sort_order(self):
        template = AttributeTemplateBuilder().with_sort_order(5).build()
        assert template.sort_order == 5


# ============================================================================
# AttributeTemplate -- update
# ============================================================================


class TestAttributeTemplateUpdate:
    def test_update_name_i18n(self):
        template = AttributeTemplateBuilder().build()
        template.update(name_i18n=_i18n("New"))
        assert template.name_i18n == _i18n("New")

    def test_update_description_i18n(self):
        template = AttributeTemplateBuilder().build()
        template.update(description_i18n=_i18n("Desc"))
        assert template.description_i18n == _i18n("Desc")

    def test_update_sort_order(self):
        template = AttributeTemplateBuilder().build()
        template.update(sort_order=10)
        assert template.sort_order == 10

    def test_update_rejects_unknown_field(self):
        template = AttributeTemplateBuilder().build()
        with pytest.raises(TypeError):
            template.update(unknown="x")


# ============================================================================
# AttributeTemplate -- __setattr__ guard
# ============================================================================


class TestAttributeTemplateGuard:
    def test_direct_code_assignment_raises(self):
        template = AttributeTemplateBuilder().build()
        with pytest.raises(AttributeError, match="Cannot set 'code' directly"):
            template.code = "new-code"


# ============================================================================
# AttributeTemplate -- deletion validation
# ============================================================================


class TestAttributeTemplateDeletion:
    def test_deletable_when_no_category_refs(self):
        template = AttributeTemplateBuilder().build()
        # Should not raise
        template.validate_deletable(has_category_refs=False)

    def test_not_deletable_when_has_category_refs(self):
        template = AttributeTemplateBuilder().build()
        with pytest.raises(AttributeTemplateHasCategoryReferencesError):
            template.validate_deletable(has_category_refs=True)


# ============================================================================
# TemplateAttributeBinding -- create
# ============================================================================


class TestTemplateAttributeBindingCreate:
    def test_create_valid(self):
        binding = TemplateAttributeBindingBuilder().build()
        assert isinstance(binding.id, uuid.UUID)

    def test_create_default_requirement_level(self):
        binding = TemplateAttributeBindingBuilder().build()
        assert binding.requirement_level == RequirementLevel.OPTIONAL

    def test_create_with_requirement_level(self):
        binding = TemplateAttributeBindingBuilder().as_required().build()
        assert binding.requirement_level == RequirementLevel.REQUIRED

    def test_create_rejects_negative_sort_order(self):
        with pytest.raises(ValueError, match="sort_order must be non-negative"):
            TemplateAttributeBinding.create(
                template_id=uuid.uuid4(),
                attribute_id=uuid.uuid4(),
                sort_order=-1,
            )

    def test_create_with_valid_filter_settings(self):
        binding = (
            TemplateAttributeBindingBuilder()
            .with_filter_settings({"widget": "slider", "min": 0, "max": 100})
            .build()
        )
        assert binding.filter_settings == {"widget": "slider", "min": 0, "max": 100}

    def test_create_rejects_invalid_filter_settings_keys(self):
        with pytest.raises(ValueError, match="unknown keys"):
            TemplateAttributeBinding.create(
                template_id=uuid.uuid4(),
                attribute_id=uuid.uuid4(),
                filter_settings={"unknown_key": "value"},
            )

    def test_create_rejects_non_dict_filter_settings(self):
        with pytest.raises(ValueError, match="must be a JSON object"):
            TemplateAttributeBinding.create(
                template_id=uuid.uuid4(),
                attribute_id=uuid.uuid4(),
                # filter_settings="not a dict",  # type: ignore[arg-type]
            )

    def test_create_rejects_too_many_filter_keys(self):
        # _FILTER_SETTINGS_MAX_KEYS = 20, so 21 keys should fail.
        # Count check happens before allowed-key check, so arbitrary keys work.
        big_settings = {f"key_{i}": i for i in range(21)}
        with pytest.raises(ValueError, match="too many keys"):
            TemplateAttributeBinding.create(
                template_id=uuid.uuid4(),
                attribute_id=uuid.uuid4(),
                filter_settings=big_settings,
            )


# ============================================================================
# TemplateAttributeBinding -- update
# ============================================================================


class TestTemplateAttributeBindingUpdate:
    def test_update_sort_order(self):
        binding = TemplateAttributeBindingBuilder().build()
        binding.update(sort_order=5)
        assert binding.sort_order == 5

    def test_update_requirement_level(self):
        binding = TemplateAttributeBindingBuilder().build()
        binding.update(requirement_level=RequirementLevel.REQUIRED)
        assert binding.requirement_level == RequirementLevel.REQUIRED

    def test_update_filter_settings(self):
        binding = TemplateAttributeBindingBuilder().build()
        binding.update(filter_settings={"widget": "checkbox"})
        assert binding.filter_settings == {"widget": "checkbox"}

    def test_update_rejects_unknown_field(self):
        binding = TemplateAttributeBindingBuilder().build()
        with pytest.raises(TypeError):
            binding.update(unknown="x")
