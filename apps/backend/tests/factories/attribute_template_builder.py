# tests/factories/attribute_template_builder.py
"""Fluent Builders for AttributeTemplate and TemplateAttributeBinding entities."""

from __future__ import annotations

import uuid
from typing import Any

from src.modules.catalog.domain.entities import (
    AttributeTemplate,
    TemplateAttributeBinding,
)
from src.modules.catalog.domain.value_objects import RequirementLevel


class AttributeTemplateBuilder:
    """Fluent builder for AttributeTemplate entities with sensible defaults.

    Usage:
        template = AttributeTemplateBuilder().build()
        template = (
            AttributeTemplateBuilder()
            .with_code("shoes")
            .with_name_i18n({"en": "Shoes Template", "ru": "Шаблон обуви"})
            .build()
        )
    """

    def __init__(self) -> None:
        self._code: str | None = None
        self._name_i18n: dict[str, str] = {
            "en": "Test Template",
            "ru": "Тестовый шаблон",
        }
        self._description_i18n: dict[str, str] | None = None
        self._sort_order: int = 0

    def with_code(self, code: str) -> AttributeTemplateBuilder:
        self._code = code
        return self

    def with_name_i18n(self, name_i18n: dict[str, str]) -> AttributeTemplateBuilder:
        self._name_i18n = name_i18n
        return self

    def with_description_i18n(
        self, description_i18n: dict[str, str]
    ) -> AttributeTemplateBuilder:
        self._description_i18n = description_i18n
        return self

    def with_sort_order(self, sort_order: int) -> AttributeTemplateBuilder:
        self._sort_order = sort_order
        return self

    def build(self) -> AttributeTemplate:
        """Build an AttributeTemplate via AttributeTemplate.create() factory method."""
        code = self._code or f"tmpl-{uuid.uuid4().hex[:6]}"
        return AttributeTemplate.create(
            code=code,
            name_i18n=self._name_i18n,
            description_i18n=self._description_i18n,
            sort_order=self._sort_order,
        )


class TemplateAttributeBindingBuilder:
    """Fluent builder for TemplateAttributeBinding entities with sensible defaults.

    Usage:
        binding = TemplateAttributeBindingBuilder().build()
        binding = (
            TemplateAttributeBindingBuilder()
            .with_template_id(template.id)
            .with_attribute_id(attr.id)
            .as_required()
            .build()
        )
    """

    def __init__(self) -> None:
        self._template_id: uuid.UUID | None = None
        self._attribute_id: uuid.UUID | None = None
        self._sort_order: int = 0
        self._requirement_level: RequirementLevel = RequirementLevel.OPTIONAL
        self._filter_settings: dict[str, Any] | None = None

    def with_template_id(
        self, template_id: uuid.UUID
    ) -> TemplateAttributeBindingBuilder:
        self._template_id = template_id
        return self

    def with_attribute_id(
        self, attribute_id: uuid.UUID
    ) -> TemplateAttributeBindingBuilder:
        self._attribute_id = attribute_id
        return self

    def with_sort_order(self, sort_order: int) -> TemplateAttributeBindingBuilder:
        self._sort_order = sort_order
        return self

    def as_required(self) -> TemplateAttributeBindingBuilder:
        self._requirement_level = RequirementLevel.REQUIRED
        return self

    def as_recommended(self) -> TemplateAttributeBindingBuilder:
        self._requirement_level = RequirementLevel.RECOMMENDED
        return self

    def as_optional(self) -> TemplateAttributeBindingBuilder:
        self._requirement_level = RequirementLevel.OPTIONAL
        return self

    def with_filter_settings(
        self, settings: dict[str, Any]
    ) -> TemplateAttributeBindingBuilder:
        self._filter_settings = settings
        return self

    def build(self) -> TemplateAttributeBinding:
        """Build a TemplateAttributeBinding via create() factory method."""
        template_id = self._template_id or uuid.uuid4()
        attribute_id = self._attribute_id or uuid.uuid4()
        return TemplateAttributeBinding.create(
            template_id=template_id,
            attribute_id=attribute_id,
            sort_order=self._sort_order,
            requirement_level=self._requirement_level,
            filter_settings=self._filter_settings,
        )
