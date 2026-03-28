# tests/factories/attribute_builder.py
"""Fluent Builders for Attribute, AttributeValue, and ProductAttributeValue entities."""

from __future__ import annotations

import uuid
from typing import Any

from src.modules.catalog.domain.entities import (
    Attribute,
    AttributeValue,
    ProductAttributeValue,
)
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    BehaviorFlags,
)


class AttributeBuilder:
    """Fluent builder for Attribute entities with sensible defaults.

    Usage:
        attr = AttributeBuilder().build()
        attr = (
            AttributeBuilder()
            .with_code("color")
            .with_data_type(AttributeDataType.STRING)
            .at_variant_level()
            .build()
        )
    """

    def __init__(self) -> None:
        self._code: str | None = None
        self._slug: str | None = None
        self._name_i18n: dict[str, str] = {
            "en": "Test Attribute",
            "ru": "Тестовый атрибут",
        }
        self._data_type: AttributeDataType = AttributeDataType.STRING
        self._ui_type: AttributeUIType = AttributeUIType.DROPDOWN
        self._is_dictionary: bool = True
        self._group_id: uuid.UUID | None = None
        self._description_i18n: dict[str, str] | None = None
        self._level: AttributeLevel = AttributeLevel.PRODUCT
        self._behavior: BehaviorFlags | None = None
        self._validation_rules: dict[str, Any] | None = None

    def with_code(self, code: str) -> AttributeBuilder:
        self._code = code
        return self

    def with_slug(self, slug: str) -> AttributeBuilder:
        self._slug = slug
        return self

    def with_name_i18n(self, name_i18n: dict[str, str]) -> AttributeBuilder:
        self._name_i18n = name_i18n
        return self

    def with_data_type(self, data_type: AttributeDataType) -> AttributeBuilder:
        self._data_type = data_type
        return self

    def with_ui_type(self, ui_type: AttributeUIType) -> AttributeBuilder:
        self._ui_type = ui_type
        return self

    def as_dictionary(self) -> AttributeBuilder:
        self._is_dictionary = True
        return self

    def as_non_dictionary(self) -> AttributeBuilder:
        self._is_dictionary = False
        return self

    def with_group_id(self, group_id: uuid.UUID) -> AttributeBuilder:
        self._group_id = group_id
        return self

    def with_description_i18n(
        self, description_i18n: dict[str, str]
    ) -> AttributeBuilder:
        self._description_i18n = description_i18n
        return self

    def at_variant_level(self) -> AttributeBuilder:
        self._level = AttributeLevel.VARIANT
        return self

    def at_product_level(self) -> AttributeBuilder:
        self._level = AttributeLevel.PRODUCT
        return self

    def with_behavior(self, behavior: BehaviorFlags) -> AttributeBuilder:
        self._behavior = behavior
        return self

    def with_validation_rules(
        self, rules: dict[str, Any]
    ) -> AttributeBuilder:
        self._validation_rules = rules
        return self

    def build(self) -> Attribute:
        """Build an Attribute via Attribute.create() factory method."""
        code = self._code or f"attr-{uuid.uuid4().hex[:6]}"
        slug = self._slug or f"attr-{uuid.uuid4().hex[:6]}"
        group_id = self._group_id or uuid.uuid4()
        return Attribute.create(
            code=code,
            slug=slug,
            name_i18n=self._name_i18n,
            data_type=self._data_type,
            ui_type=self._ui_type,
            is_dictionary=self._is_dictionary,
            group_id=group_id,
            description_i18n=self._description_i18n,
            level=self._level,
            behavior=self._behavior,
            validation_rules=self._validation_rules,
        )


class AttributeValueBuilder:
    """Fluent builder for AttributeValue entities with sensible defaults.

    Usage:
        value = AttributeValueBuilder().build()
        value = (
            AttributeValueBuilder()
            .with_attribute_id(attr.id)
            .with_code("red")
            .build()
        )
    """

    def __init__(self) -> None:
        self._attribute_id: uuid.UUID | None = None
        self._code: str | None = None
        self._slug: str | None = None
        self._value_i18n: dict[str, str] = {
            "en": "Test Value",
            "ru": "Тестовое значение",
        }
        self._search_aliases: list[str] | None = None
        self._meta_data: dict[str, Any] | None = None
        self._value_group: str | None = None
        self._sort_order: int = 0
        self._is_active: bool = True

    def with_attribute_id(self, attribute_id: uuid.UUID) -> AttributeValueBuilder:
        self._attribute_id = attribute_id
        return self

    def with_code(self, code: str) -> AttributeValueBuilder:
        self._code = code
        return self

    def with_slug(self, slug: str) -> AttributeValueBuilder:
        self._slug = slug
        return self

    def with_value_i18n(self, value_i18n: dict[str, str]) -> AttributeValueBuilder:
        self._value_i18n = value_i18n
        return self

    def with_search_aliases(self, aliases: list[str]) -> AttributeValueBuilder:
        self._search_aliases = aliases
        return self

    def with_meta_data(self, meta_data: dict[str, Any]) -> AttributeValueBuilder:
        self._meta_data = meta_data
        return self

    def with_value_group(self, group: str) -> AttributeValueBuilder:
        self._value_group = group
        return self

    def with_sort_order(self, sort_order: int) -> AttributeValueBuilder:
        self._sort_order = sort_order
        return self

    def as_inactive(self) -> AttributeValueBuilder:
        self._is_active = False
        return self

    def build(self) -> AttributeValue:
        """Build an AttributeValue via AttributeValue.create() factory method."""
        attribute_id = self._attribute_id or uuid.uuid4()
        code = self._code or f"val-{uuid.uuid4().hex[:6]}"
        slug = self._slug or f"val-{uuid.uuid4().hex[:6]}"
        return AttributeValue.create(
            attribute_id=attribute_id,
            code=code,
            slug=slug,
            value_i18n=self._value_i18n,
            search_aliases=self._search_aliases,
            meta_data=self._meta_data,
            value_group=self._value_group,
            sort_order=self._sort_order,
            is_active=self._is_active,
        )


class ProductAttributeValueBuilder:
    """Fluent builder for ProductAttributeValue (EAV pivot) entities.

    Usage:
        pav = ProductAttributeValueBuilder().build()
        pav = (
            ProductAttributeValueBuilder()
            .with_product_id(product.id)
            .with_attribute_id(attr.id)
            .with_attribute_value_id(val.id)
            .build()
        )
    """

    def __init__(self) -> None:
        self._product_id: uuid.UUID | None = None
        self._attribute_id: uuid.UUID | None = None
        self._attribute_value_id: uuid.UUID | None = None

    def with_product_id(self, product_id: uuid.UUID) -> ProductAttributeValueBuilder:
        self._product_id = product_id
        return self

    def with_attribute_id(
        self, attribute_id: uuid.UUID
    ) -> ProductAttributeValueBuilder:
        self._attribute_id = attribute_id
        return self

    def with_attribute_value_id(
        self, attribute_value_id: uuid.UUID
    ) -> ProductAttributeValueBuilder:
        self._attribute_value_id = attribute_value_id
        return self

    def build(self) -> ProductAttributeValue:
        """Build a ProductAttributeValue via ProductAttributeValue.create()."""
        return ProductAttributeValue.create(
            product_id=self._product_id or uuid.uuid4(),
            attribute_id=self._attribute_id or uuid.uuid4(),
            attribute_value_id=self._attribute_value_id or uuid.uuid4(),
        )
