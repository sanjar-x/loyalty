# tests/factories/catalog_mothers.py
"""Object Mothers for Catalog module domain entities.

Mothers are thin wrappers around the fluent Builders (per D-01).
They provide preset configurations for common test scenarios.
"""

import uuid
from typing import Any

from src.modules.catalog.domain.entities import (
    Attribute,
    AttributeGroup,
    AttributeValue,
    Brand,
    Category,
)
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    BehaviorFlags,
)
from tests.factories.attribute_builder import AttributeBuilder, AttributeValueBuilder
from tests.factories.attribute_group_builder import AttributeGroupBuilder
from tests.factories.brand_builder import BrandBuilder


class BrandMothers:
    """Pre-built Brand aggregate configurations."""

    @staticmethod
    def default() -> Brand:
        """Default brand with sensible test defaults."""
        return BrandBuilder().build()

    @staticmethod
    def with_logo() -> Brand:
        """Brand with a logo URL."""
        return BrandBuilder().with_logo("https://example.com/logo.png").build()


class CategoryMothers:
    """Pre-built Category aggregate configurations."""

    @staticmethod
    def root(
        name_i18n: dict[str, str] | None = None,
        slug: str | None = None,
    ) -> Category:
        """Root-level category (level=0, no parent)."""
        return Category.create_root(
            name_i18n=name_i18n or {"en": "Electronics", "ru": "Электроника"},
            slug=slug or f"electronics-{uuid.uuid4().hex[:6]}",
            sort_order=0,
        )

    @staticmethod
    def child(
        parent: Category | None = None,
        name_i18n: dict[str, str] | None = None,
    ) -> Category:
        """Child category under given parent (or creates a root parent)."""
        if parent is None:
            parent = CategoryMothers.root()
        return Category.create_child(
            name_i18n=name_i18n or {"en": "Smartphones", "ru": "Смартфоны"},
            slug=f"smartphones-{uuid.uuid4().hex[:6]}",
            parent=parent,
            sort_order=0,
        )

    @staticmethod
    def deep_nested(depth: int = 3) -> list[Category]:
        """Chain of nested categories up to the given depth."""
        categories: list[Category] = []
        names = ["Electronics", "Smartphones", "Android", "Samsung", "Galaxy"]
        ru_names = ["Электроника", "Смартфоны", "Андроид", "Самсунг", "Галакси"]
        root = CategoryMothers.root(name_i18n={"en": names[0], "ru": ru_names[0]})
        categories.append(root)
        for i in range(1, min(depth, len(names))):
            child = Category.create_child(
                name_i18n={"en": names[i], "ru": ru_names[i]},
                slug=f"{names[i].lower()}-{uuid.uuid4().hex[:6]}",
                parent=categories[-1],
                sort_order=0,
            )
            categories.append(child)
        return categories


class AttributeGroupMothers:
    """Pre-built AttributeGroup aggregate configurations."""

    @staticmethod
    def general() -> AttributeGroup:
        """The default 'general' group that always exists."""
        return (
            AttributeGroupBuilder()
            .with_code("general")
            .with_name_i18n({"en": "General", "ru": "Общие"})
            .build()
        )

    @staticmethod
    def physical() -> AttributeGroup:
        """Physical characteristics group."""
        return (
            AttributeGroupBuilder()
            .with_code(f"physical-{uuid.uuid4().hex[:6]}")
            .with_name_i18n(
                {
                    "en": "Physical Characteristics",
                    "ru": "Физические характеристики",
                }
            )
            .with_sort_order(1)
            .build()
        )

    @staticmethod
    def technical() -> AttributeGroup:
        """Technical specifications group."""
        return (
            AttributeGroupBuilder()
            .with_code(f"technical-{uuid.uuid4().hex[:6]}")
            .with_name_i18n({"en": "Technical", "ru": "Технические"})
            .with_sort_order(2)
            .build()
        )

    @staticmethod
    def custom(
        code: str | None = None,
        name_i18n: dict[str, str] | None = None,
        sort_order: int = 0,
    ) -> AttributeGroup:
        """Custom group with overridable fields."""
        builder = AttributeGroupBuilder().with_sort_order(sort_order)
        if code:
            builder = builder.with_code(code)
        if name_i18n:
            builder = builder.with_name_i18n(name_i18n)
        return builder.build()


class AttributeMothers:
    """Pre-built Attribute aggregate configurations."""

    @staticmethod
    def string_dictionary(
        code: str | None = None,
        group_id: uuid.UUID | None = None,
        **overrides: Any,
    ) -> Attribute:
        """String-type dictionary attribute (e.g. Color, Material)."""
        return Attribute.create(
            code=code or f"color-{uuid.uuid4().hex[:6]}",
            slug=f"color-{uuid.uuid4().hex[:6]}",
            name_i18n={"en": "Color", "ru": "Цвет"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.COLOR_SWATCH,
            is_dictionary=True,
            group_id=group_id or uuid.uuid4(),
            **overrides,
        )

    @staticmethod
    def numeric_non_dictionary(
        code: str | None = None,
        group_id: uuid.UUID | None = None,
        **overrides: Any,
    ) -> Attribute:
        """Numeric non-dictionary attribute (e.g. Screen Size, Weight)."""
        return Attribute.create(
            code=code or f"screen-size-{uuid.uuid4().hex[:6]}",
            slug=f"screen-size-{uuid.uuid4().hex[:6]}",
            name_i18n={"en": "Screen Size", "ru": "Размер экрана"},
            data_type=AttributeDataType.FLOAT,
            ui_type=AttributeUIType.RANGE_SLIDER,
            is_dictionary=False,
            group_id=group_id or uuid.uuid4(),
            is_filterable=True,
            is_comparable=True,
            **overrides,
        )

    @staticmethod
    def boolean_attribute(
        code: str | None = None,
        group_id: uuid.UUID | None = None,
    ) -> Attribute:
        """Boolean attribute (e.g. Is Waterproof)."""
        return Attribute.create(
            code=code or f"waterproof-{uuid.uuid4().hex[:6]}",
            slug=f"waterproof-{uuid.uuid4().hex[:6]}",
            name_i18n={"en": "Is Waterproof", "ru": "Водонепроницаемый"},
            data_type=AttributeDataType.BOOLEAN,
            ui_type=AttributeUIType.CHECKBOX,
            is_dictionary=False,
            group_id=group_id or uuid.uuid4(),
        )

    @staticmethod
    def variant_level(
        code: str | None = None,
        group_id: uuid.UUID | None = None,
    ) -> Attribute:
        """Variant-level attribute (e.g. Size)."""
        return (
            AttributeBuilder()
            .with_code(code or f"size-{uuid.uuid4().hex[:6]}")
            .with_slug(f"size-{uuid.uuid4().hex[:6]}")
            .with_name_i18n({"en": "Size", "ru": "Размер"})
            .with_data_type(AttributeDataType.STRING)
            .with_ui_type(AttributeUIType.TEXT_BUTTON)
            .as_dictionary()
            .with_group_id(group_id or uuid.uuid4())
            .at_variant_level()
            .with_behavior(
                BehaviorFlags(
                    is_filterable=True,
                    is_visible_on_card=True,
                )
            )
            .build()
        )


class AttributeValueMothers:
    """Pre-built AttributeValue configurations."""

    @staticmethod
    def color_red(attribute_id: uuid.UUID | None = None) -> AttributeValue:
        """Red color value with hex metadata."""
        return (
            AttributeValueBuilder()
            .with_attribute_id(attribute_id or uuid.uuid4())
            .with_code(f"red-{uuid.uuid4().hex[:6]}")
            .with_slug(f"red-{uuid.uuid4().hex[:6]}")
            .with_value_i18n({"en": "Red", "ru": "Красный"})
            .with_search_aliases(["scarlet", "crimson"])
            .with_meta_data({"hex": "#FF0000"})
            .with_value_group("Warm tones")
            .build()
        )

    @staticmethod
    def color_blue(attribute_id: uuid.UUID | None = None) -> AttributeValue:
        """Blue color value with hex metadata."""
        return (
            AttributeValueBuilder()
            .with_attribute_id(attribute_id or uuid.uuid4())
            .with_code(f"blue-{uuid.uuid4().hex[:6]}")
            .with_slug(f"blue-{uuid.uuid4().hex[:6]}")
            .with_value_i18n({"en": "Blue", "ru": "Синий"})
            .with_search_aliases(["navy", "azure"])
            .with_meta_data({"hex": "#0000FF"})
            .with_value_group("Cool tones")
            .with_sort_order(1)
            .build()
        )

    @staticmethod
    def size_xl(attribute_id: uuid.UUID | None = None) -> AttributeValue:
        """XL size value (no metadata)."""
        return (
            AttributeValueBuilder()
            .with_attribute_id(attribute_id or uuid.uuid4())
            .with_code(f"xl-{uuid.uuid4().hex[:6]}")
            .with_slug(f"xl-{uuid.uuid4().hex[:6]}")
            .with_value_i18n({"en": "XL", "ru": "XL"})
            .with_sort_order(3)
            .build()
        )

    @staticmethod
    def custom(
        attribute_id: uuid.UUID | None = None,
        code: str | None = None,
        slug: str | None = None,
        value_i18n: dict[str, str] | None = None,
        **kwargs,
    ) -> AttributeValue:
        """Custom value with overridable fields."""
        from src.modules.catalog.domain.entities import AttributeValue

        return AttributeValue.create(
            attribute_id=attribute_id or uuid.uuid4(),
            code=code or f"val-{uuid.uuid4().hex[:6]}",
            slug=slug or f"val-{uuid.uuid4().hex[:6]}",
            value_i18n=value_i18n
            or {"en": "Custom Value", "ru": "Пользовательское значение"},
            **kwargs,
        )
