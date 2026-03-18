# tests/factories/catalog_mothers.py
"""Object Mothers for Catalog module domain entities."""

import uuid

from src.modules.catalog.domain.entities import AttributeGroup, Brand, Category


class BrandMothers:
    """Pre-built Brand aggregate configurations."""

    @staticmethod
    def without_logo() -> Brand:
        """Brand with no logo -- simplest valid state."""
        return Brand.create(name="Test Brand", slug=f"test-brand-{uuid.uuid4().hex[:6]}")

    @staticmethod
    def with_pending_logo() -> Brand:
        """Brand with logo in PENDING_UPLOAD state."""
        brand = Brand.create(name="Logo Brand", slug=f"logo-brand-{uuid.uuid4().hex[:6]}")
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
    def root(name: str = "Electronics", slug: str | None = None) -> Category:
        """Root-level category (level=0, no parent)."""
        return Category.create_root(
            name=name,
            slug=slug or f"electronics-{uuid.uuid4().hex[:6]}",
            sort_order=0,
        )

    @staticmethod
    def child(parent: Category | None = None, name: str = "Smartphones") -> Category:
        """Child category under given parent (or creates a root parent)."""
        if parent is None:
            parent = CategoryMothers.root()
        return Category.create_child(
            name=name,
            slug=f"smartphones-{uuid.uuid4().hex[:6]}",
            parent=parent,
            sort_order=0,
        )

    @staticmethod
    def deep_nested(depth: int = 3) -> list[Category]:
        """Chain of nested categories up to the given depth. Returns [root, child, grandchild, ...]."""
        categories: list[Category] = []
        names = ["Electronics", "Smartphones", "Android", "Samsung", "Galaxy"]
        root = CategoryMothers.root(name=names[0])
        categories.append(root)
        for i in range(1, min(depth, len(names))):
            child = Category.create_child(
                name=names[i],
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
            name_i18n={"en": "Physical Characteristics", "ru": "Физические характеристики"},
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
