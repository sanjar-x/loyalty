# tests/factories/catalog_mothers.py
"""Object Mothers for Catalog module domain entities."""

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
)


class BrandMothers:
    """Pre-built Brand aggregate configurations."""

    @staticmethod
    def without_logo() -> Brand:
        """Brand with no logo -- simplest valid state."""
        return Brand.create(
            name="Test Brand", slug=f"test-brand-{uuid.uuid4().hex[:6]}"
        )

    @staticmethod
    def with_pending_logo() -> Brand:
        """Brand with logo in PENDING_UPLOAD state."""
        brand = Brand.create(
            name="Logo Brand", slug=f"logo-brand-{uuid.uuid4().hex[:6]}"
        )
        brand.init_logo_upload(
            object_key=f"raw_uploads/catalog/brands/{brand.id}/logo_raw",
            content_type="image/png",
        )
        brand.clear_domain_events()
        return brand

    @staticmethod
    def with_processing_logo() -> Brand:
        """Brand with logo in PROCESSING state (upload confirmed)."""
        brand = BrandMothers.with_pending_logo()
        brand.confirm_logo_upload()
        brand.clear_domain_events()
        return brand

    @staticmethod
    def with_completed_logo() -> Brand:
        """Brand with logo in COMPLETED state."""
        brand = BrandMothers.with_processing_logo()
        brand.complete_logo_processing(
            url="https://cdn.test/logo.webp",
            object_key=f"processed/catalog/brands/{brand.id}/logo.webp",
            content_type="image/webp",
            size_bytes=2048,
        )
        brand.clear_domain_events()
        return brand

    @staticmethod
    def with_failed_logo() -> Brand:
        """Brand with logo in FAILED state."""
        brand = BrandMothers.with_processing_logo()
        brand.fail_logo_processing()
        brand.clear_domain_events()
        return brand


class CategoryMothers:
    """Pre-built Category aggregate configurations."""

    @staticmethod
    def root(
        name_i18n: dict[str, str] | None = None,
        slug: str | None = None,
    ) -> Category:
        """Root-level category (level=0, no parent)."""
        return Category.create_root(
            name_i18n=name_i18n or {"en": "Electronics"},
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
            name_i18n=name_i18n or {"en": "Smartphones"},
            slug=f"smartphones-{uuid.uuid4().hex[:6]}",
            parent=parent,
            sort_order=0,
        )

    @staticmethod
    def deep_nested(depth: int = 3) -> list[Category]:
        """Chain of nested categories up to the given depth."""
        categories: list[Category] = []
        names = ["Electronics", "Smartphones", "Android", "Samsung", "Galaxy"]
        root = CategoryMothers.root(name_i18n={"en": names[0]})
        categories.append(root)
        for i in range(1, min(depth, len(names))):
            child = Category.create_child(
                name_i18n={"en": names[i]},
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
        return AttributeGroup.create(
            code="general",
            name_i18n={"en": "General", "ru": "Общие"},
            sort_order=0,
        )

    @staticmethod
    def physical() -> AttributeGroup:
        """Physical characteristics group."""
        return AttributeGroup.create(
            code=f"physical-{uuid.uuid4().hex[:6]}",
            name_i18n={
                "en": "Physical Characteristics",
                "ru": "Физические характеристики",
            },
            sort_order=1,
        )

    @staticmethod
    def technical() -> AttributeGroup:
        """Technical specifications group."""
        return AttributeGroup.create(
            code=f"technical-{uuid.uuid4().hex[:6]}",
            name_i18n={"en": "Technical", "ru": "Технические"},
            sort_order=2,
        )

    @staticmethod
    def custom(
        code: str | None = None,
        name_i18n: dict[str, str] | None = None,
        sort_order: int = 0,
    ) -> AttributeGroup:
        """Custom group with overridable fields."""
        return AttributeGroup.create(
            code=code or f"custom-{uuid.uuid4().hex[:6]}",
            name_i18n=name_i18n or {"en": "Custom Group"},
            sort_order=sort_order,
        )


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
            name_i18n={"en": "Screen Size"},
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
            name_i18n={"en": "Is Waterproof"},
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
        return Attribute.create(
            code=code or f"size-{uuid.uuid4().hex[:6]}",
            slug=f"size-{uuid.uuid4().hex[:6]}",
            name_i18n={"en": "Size", "ru": "Размер"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            group_id=group_id or uuid.uuid4(),
            level=AttributeLevel.VARIANT,
            is_filterable=True,
            is_visible_on_card=True,
        )


class AttributeValueMothers:
    """Pre-built AttributeValue configurations."""

    @staticmethod
    def color_red(attribute_id: uuid.UUID | None = None) -> AttributeValue:
        """Red color value with hex metadata."""
        from src.modules.catalog.domain.entities import AttributeValue

        return AttributeValue.create(
            attribute_id=attribute_id or uuid.uuid4(),
            code=f"red-{uuid.uuid4().hex[:6]}",
            slug=f"red-{uuid.uuid4().hex[:6]}",
            value_i18n={"en": "Red", "ru": "Красный"},
            search_aliases=["scarlet", "crimson"],
            meta_data={"hex": "#FF0000"},
            value_group="Warm tones",
            sort_order=0,
        )

    @staticmethod
    def color_blue(attribute_id: uuid.UUID | None = None) -> AttributeValue:
        """Blue color value with hex metadata."""
        from src.modules.catalog.domain.entities import AttributeValue

        return AttributeValue.create(
            attribute_id=attribute_id or uuid.uuid4(),
            code=f"blue-{uuid.uuid4().hex[:6]}",
            slug=f"blue-{uuid.uuid4().hex[:6]}",
            value_i18n={"en": "Blue", "ru": "Синий"},
            search_aliases=["navy", "azure"],
            meta_data={"hex": "#0000FF"},
            value_group="Cool tones",
            sort_order=1,
        )

    @staticmethod
    def size_xl(attribute_id: uuid.UUID | None = None) -> AttributeValue:
        """XL size value (no metadata)."""
        from src.modules.catalog.domain.entities import AttributeValue

        return AttributeValue.create(
            attribute_id=attribute_id or uuid.uuid4(),
            code=f"xl-{uuid.uuid4().hex[:6]}",
            slug=f"xl-{uuid.uuid4().hex[:6]}",
            value_i18n={"en": "XL", "ru": "XL"},
            sort_order=3,
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
            value_i18n=value_i18n or {"en": "Custom Value"},
            **kwargs,
        )
