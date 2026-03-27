"""
ORM models for the Catalog bounded context.

Maps domain concepts to PostgreSQL tables via SQLAlchemy declarative mappings.
These models belong to the infrastructure layer and must never leak into the
domain or application layers -- repositories translate between ORM and domain
entities using the Data Mapper pattern.

Sections:
    1. Enumerations -- database-level enums for product status, media, etc.
    2. Taxonomy & Dictionaries -- Brand, Category, AttributeGroup, Attribute, AttributeValue.
    3. Rules -- TemplateAttributeBinding (governance).
    4. Core Domain -- Supplier, Product, MediaAsset.
    5. Variations -- SKU and SKU <-> AttributeValue link table.
"""

import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import (
    ARRAY,
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    MediaRole,
    MediaType,
    ProductStatus,
    RequirementLevel,
)

# ---------------------------------------------------------------------------
# 2. TAXONOMY & DICTIONARIES
# ---------------------------------------------------------------------------


class Brand(Base):
    """ORM model for product brands (e.g. Nike, Adidas)."""

    __tablename__ = "brands"
    __table_args__ = (
        Index("uix_brands_name", "name", unique=True),
        Index("uix_brands_slug", "slug", unique=True),
        {"comment": "Brand directory for the catalog"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        comment="Primary key (UUIDv7 for time-sortable ordering)",
    )

    name: Mapped[str] = mapped_column(String(255), comment="Brand display name")
    slug: Mapped[str] = mapped_column(
        String(255), comment="URL-safe identifier for routing"
    )
    logo_storage_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Reference to storage_objects.id in ImageBackend",
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Cached public URL from the Storage module",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Category(Base):
    """ORM model for the hierarchical product category tree.

    Uses a self-referential foreign key (``parent_id``) for the adjacency
    list pattern and a ``full_slug`` materialized path for efficient subtree
    lookups.
    """

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    full_slug: Mapped[str] = mapped_column(String(1000), index=True)
    level: Mapped[int] = mapped_column(Integer, server_default=text("0"), index=True)
    name_i18n: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attribute_templates.id", ondelete="SET NULL"),
        index=True,
        default=None,
    )
    effective_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attribute_templates.id", ondelete="SET NULL"),
        index=True,
        default=None,
        comment="Computed: own template_id or inherited from nearest ancestor",
    )

    children: Mapped[list[Category]] = relationship(
        "Category", back_populates="parent", cascade="save-update, merge"
    )
    parent: Mapped[Category] = relationship(
        "Category", back_populates="children", remote_side="Category.id"
    )
    template: Mapped[AttributeTemplate | None] = relationship(
        "AttributeTemplate", foreign_keys=[template_id]
    )

    __table_args__ = (
        Index(
            "uix_categories_slug",
            "parent_id",
            "slug",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "ix_categories_full_slug_ops",
            "full_slug",
            postgresql_ops={"full_slug": "varchar_pattern_ops"},
        ),
        Index("ix_categories_level_sort", "level", "sort_order"),
    )


class AttributeTemplate(Base):
    """ORM model for attribute templates (flat templates).

    Each template is a top-level template that defines which attributes
    apply to products via TemplateAttributeBinding governance rules.
    """

    __tablename__ = "attribute_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name_i18n: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    description_i18n: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Child aggregates
    bindings: Mapped[list[TemplateAttributeBinding]] = relationship(
        "TemplateAttributeBinding",
        back_populates="template",
        cascade="all, delete-orphan",
    )


class AttributeGroup(Base):
    """ORM model for attribute groups (logical sections for organizing attributes).

    Groups provide visual and semantic grouping of attributes in the admin UI
    and on the product card (e.g. "Physical characteristics", "Technical").
    The "general" group always exists and cannot be deleted.
    """

    __tablename__ = "attribute_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        comment="Primary key (UUIDv7)",
    )
    code: Mapped[str] = mapped_column(
        String(100),
        comment="Machine-readable unique code (e.g. 'general', 'physical')",
    )
    name_i18n: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(sqltype=JSONB),
        server_default=text("'{}'::jsonb"),
        comment="Multilingual display name",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        server_default=text("0"),
        comment="Display ordering among groups (lower = first)",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    attributes: Mapped[list[Attribute]] = relationship(
        "Attribute", back_populates="group"
    )

    __table_args__ = (
        Index("uix_attribute_groups_code", "code", unique=True),
        Index(
            "ix_attribute_groups_name_i18n_gin",
            "name_i18n",
            postgresql_using="gin",
        ),
    )


class Attribute(Base):
    """ORM model for the EAV attribute dictionary.

    Stores multilingual names/descriptions as JSONB, data-type and UI-widget
    hints, behavior flags (filterable, searchable, comparable, etc.),
    validation rules, and product/variant level.
    Each attribute belongs to exactly one :class:`AttributeGroup`.
    """

    __tablename__ = "attributes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7, comment="ID (UUIDv7)"
    )
    code: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(255))

    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attribute_groups.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
        comment="FK to attribute_groups; NULL when group is deleted without reassignment",
    )

    name_i18n: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(sqltype=JSONB), server_default=text("'{}'::jsonb")
    )
    description_i18n: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(sqltype=JSONB), server_default=text("'{}'::jsonb")
    )
    data_type: Mapped[AttributeDataType] = mapped_column(
        Enum(AttributeDataType, name="attribute_data_type_enum"),
        # PostgreSQL native enums use .name (uppercase label), not .value
        server_default=AttributeDataType.STRING.name,
    )
    ui_type: Mapped[AttributeUIType] = mapped_column(
        Enum(AttributeUIType, name="attribute_ui_type_enum"),
        server_default=AttributeUIType.TEXT_BUTTON.name,
    )
    is_dictionary: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    level: Mapped[AttributeLevel] = mapped_column(
        Enum(AttributeLevel, name="attribute_level_enum"),
        server_default=AttributeLevel.PRODUCT.name,
        comment="Product-level or variant-level attribute",
    )

    # Behavior flags
    is_filterable: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        comment="Available as filter on storefront",
    )
    is_searchable: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        comment="Participates in full-text search",
    )
    search_weight: Mapped[int] = mapped_column(
        Integer, server_default=text("5"), comment="Search ranking priority (1-10)"
    )
    is_comparable: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        comment="Shown in product comparison table",
    )
    is_visible_on_card: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), comment="Shown on product detail page"
    )

    # Validation rules (type-specific constraints stored as JSONB)
    validation_rules: Mapped[dict[str, Any] | None] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        comment="Type-specific validation constraints (e.g. min_length, max_value)",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    group: Mapped[AttributeGroup | None] = relationship(
        "AttributeGroup", back_populates="attributes"
    )
    values: Mapped[list[AttributeValue]] = relationship(
        "AttributeValue", back_populates="attribute", cascade="all, delete-orphan"
    )
    __table_args__ = (
        CheckConstraint("search_weight BETWEEN 1 AND 10", name="ck_attributes_search_weight"),
        Index("uix_attributes_code", "code", unique=True),
        Index("uix_attributes_slug", "slug", unique=True),
        Index("ix_attributes_name_i18n_gin", "name_i18n", postgresql_using="gin"),
        Index(
            "ix_attributes_filterable",
            "is_filterable",
            postgresql_where=text("is_filterable = true"),
        ),
    )


class AttributeValue(Base):
    """ORM model for concrete attribute options (e.g. Red, 42, Cotton).

    Each value belongs to exactly one :class:`Attribute` and carries
    multilingual labels, search aliases, and optional grouping metadata.
    """

    __tablename__ = "attribute_values"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    attribute_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attributes.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    value_i18n: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), server_default=text("'{}'::jsonb")
    )
    search_aliases: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default=text("'{}'::varchar[]")
    )
    # Named `meta_data` (not `metadata`) to avoid collision with SQLAlchemy Base.metadata
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), server_default=text("'{}'::jsonb")
    )
    value_group: Mapped[str | None] = mapped_column(String(100), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
        comment="Inactive values hidden from storefront but preserved on existing products",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    attribute: Mapped[Attribute] = relationship("Attribute", back_populates="values")

    __table_args__ = (
        Index("uix_attr_val_code", "attribute_id", "code", unique=True),
        Index("uix_attr_val_slug", "attribute_id", "slug", unique=True),
        Index("ix_attr_val_value_i18n_gin", "value_i18n", postgresql_using="gin"),
        Index(
            "ix_attr_val_search_aliases_gin", "search_aliases", postgresql_using="gin"
        ),
        Index(
            "ix_attr_val_active",
            "attribute_id",
            "sort_order",
            postgresql_where=text("is_active = true"),
        ),
    )


class TemplateAttributeBinding(Base):
    """ORM model for template-attribute binding governance rules.

    Many-to-many link between AttributeTemplate and Attribute with
    sort ordering, requirement level, and filter settings.
    """

    __tablename__ = "template_attribute_bindings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attribute_templates.id", ondelete="CASCADE"), index=True
    )
    attribute_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attributes.id", ondelete="CASCADE"), index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    requirement_level: Mapped[RequirementLevel] = mapped_column(
        Enum(RequirementLevel, name="requirement_level_enum", create_type=False),
        server_default=RequirementLevel.OPTIONAL.name,
    )
    filter_settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    template: Mapped[AttributeTemplate] = relationship(
        "AttributeTemplate", back_populates="bindings"
    )
    attribute: Mapped[Attribute] = relationship("Attribute")

    __table_args__ = (
        UniqueConstraint(
            "template_id", "attribute_id", name="uix_template_attr_binding"
        ),
    )


# ---------------------------------------------------------------------------
# 4. CORE DOMAIN
# ---------------------------------------------------------------------------


class Product(Base):
    """ORM model for the central product entity.

    Carries multilingual content (JSONB), lifecycle status, soft-delete
    timestamp, and optimistic-locking ``version`` column. Related SKUs,
    media assets, and attribute values hang off this model.
    """

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    primary_category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="RESTRICT"), index=True
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True
    )
    slug: Mapped[str] = mapped_column(String(255))

    title_i18n: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), server_default=text("'{}'::jsonb")
    )
    description_i18n: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), server_default=text("'{}'::jsonb")
    )
    popularity_score: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    country_of_origin: Mapped[str | None] = mapped_column(String(2))
    attributes: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), server_default=text("'{}'::jsonb")
    )
    source_url: Mapped[str | None] = mapped_column(String(1024))
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default=text("'{}'::varchar[]")
    )

    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status_enum"),
        server_default=ProductStatus.DRAFT.name,
        index=True,
    )
    is_visible: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    version: Mapped[int] = mapped_column(
        Integer, server_default=text("1"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), index=True
    )
    supplier: Mapped["Supplier"] = relationship(  # noqa: F821, UP037  # ty:ignore[unresolved-reference]
        "src.modules.supplier.infrastructure.models.Supplier",
        back_populates="products",
        foreign_keys="[Product.supplier_id]",
    )
    variants: Mapped[list[ProductVariant]] = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan"
    )
    media_assets: Mapped[list[MediaAsset]] = relationship(
        "MediaAsset", back_populates="product", cascade="all, delete-orphan"
    )
    product_attribute_values: Mapped[list[ProductAttributeValue]] = relationship(
        "ProductAttributeValue",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    __mapper_args__: ClassVar[dict[str, Any]] = {
        "version_id_col": version,
    }

    __table_args__ = (
        Index(
            "uix_products_slug",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_products_published_at",
            "published_at",
            postgresql_where=text("deleted_at IS NULL AND published_at IS NOT NULL"),
        ),
        Index("ix_products_attributes_gin", "attributes", postgresql_using="gin"),
        Index("ix_products_title_gin", "title_i18n", postgresql_using="gin"),
        Index("ix_products_tags_gin", "tags", postgresql_using="gin"),
        # catalog_listing: covers queries that filter by status (e.g. admin listing by DRAFT/ACTIVE).
        # sale_listing: covers storefront queries that don't filter by status but sort by popularity.
        # Both are partial indexes on visible, non-deleted products. They differ in the "status" column
        # inclusion, which avoids an index-filter step for each respective query pattern.
        Index(
            "ix_products_catalog_listing",
            "brand_id",
            "primary_category_id",
            "status",
            "popularity_score",
            postgresql_where=text("deleted_at IS NULL AND is_visible = true"),
        ),
        Index(
            "ix_products_sale_listing",
            "brand_id",
            "primary_category_id",
            "popularity_score",
            postgresql_where=text("deleted_at IS NULL AND is_visible = true"),
        ),
    )


class ProductVariant(Base):
    """ORM model for product variants (named variation groupings).

    Each variant represents a tab in the admin UI with its own name,
    media, and set of SKUs. Child of Product, parent of SKU.
    """

    __tablename__ = "product_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
    )
    name_i18n: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB), server_default=text("'{}'::jsonb")
    )
    description_i18n: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    default_price: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Default price in smallest currency units"
    )
    default_currency: Mapped[str] = mapped_column(
        String(3),
        ForeignKey("currencies.code", ondelete="RESTRICT"),
        server_default=text("'RUB'"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    product: Mapped[Product] = relationship("Product", back_populates="variants")
    skus: Mapped[list[SKU]] = relationship(
        "SKU", back_populates="variant", cascade="all, delete-orphan"
    )
    media_assets: Mapped[list[MediaAsset]] = relationship(
        "MediaAsset", back_populates="variant", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_product_variants_product_id", "product_id"),)


class MediaAsset(Base):
    """ORM model for product media assets (business context).

    Describes *how* a file is used in the catalog -- its role, display
    order, and optional variant binding.  The physical file data
    lives in the Storage module (:class:`StorageObject`).
    """

    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True, index=True
    )

    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type_enum"),
        server_default=MediaType.IMAGE.name,
        index=True,
    )
    role: Mapped[MediaRole] = mapped_column(
        Enum(MediaRole, name="media_role_enum"),
        server_default=MediaRole.GALLERY.name,
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    # Soft-link to the Storage module
    storage_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        index=True,
        nullable=True,
        comment="Reference to storage_objects.id (unified file registry)",
    )

    is_external: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        comment="True when the resource is hosted externally (not in our S3)",
    )

    url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Public URL of the media asset",
    )

    image_variants: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Image size variants: [{size, width, height, url}, ...]",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    product: Mapped[Product] = relationship("Product", back_populates="media_assets")
    variant: Mapped[ProductVariant | None] = relationship(
        "ProductVariant", back_populates="media_assets"
    )

    __table_args__ = (
        # Business rule: each variant may have at most one MAIN image
        Index(
            "uix_media_single_main_per_variant",
            "product_id",
            "variant_id",
            unique=True,
            postgresql_where=text(f"role = '{MediaRole.MAIN.name}'"),
            postgresql_nulls_not_distinct=True,
        ),
        # Composite index for list_by_product queries
        Index(
            "ix_media_assets_product_variant_sort",
            "product_id",
            "variant_id",
            "sort_order",
        ),
    )


# ---------------------------------------------------------------------------
# 5. VARIATIONS
# ---------------------------------------------------------------------------


class SKU(Base):
    """ORM model for Stock Keeping Units (purchasable items within a variant).

    Each SKU represents a unique combination of attribute values
    (e.g. size + colour) for a parent :class:`Product`.  Carries
    pricing, an activation flag, and optimistic-locking ``version``.
    """

    __tablename__ = "skus"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), index=True
    )
    sku_code: Mapped[str] = mapped_column(String(100))
    variant_hash: Mapped[str] = mapped_column(String(64))
    main_image_url: Mapped[str | None] = mapped_column(String(1024))
    attributes_cache: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), server_default=text("'{}'::jsonb")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    version: Mapped[int] = mapped_column(
        Integer, server_default=text("1"), nullable=False
    )

    price: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Base price in smallest currency units (e.g. kopecks), nullable — inherits from variant",
    )

    compare_at_price: Mapped[int | None] = mapped_column(
        Integer, comment="Previous price for strikethrough display"
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        ForeignKey("currencies.code", ondelete="RESTRICT"),
        server_default=text("'RUB'"),
        comment="ISO 4217 currency code (FK → geo.currencies)",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), index=True
    )

    product: Mapped[Product] = relationship("Product")
    variant: Mapped[ProductVariant] = relationship(
        "ProductVariant", back_populates="skus"
    )
    attribute_values: Mapped[list[SKUAttributeValueLink]] = relationship(
        "SKUAttributeValueLink", back_populates="sku", cascade="all, delete-orphan"
    )

    __mapper_args__: ClassVar[dict[str, Any]] = {
        "version_id_col": version,
    }

    __table_args__ = (
        Index(
            "uix_skus_sku_code",
            "sku_code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uix_skus_variant_hash",
            "variant_hash",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class SKUAttributeValueLink(Base):
    """Many-to-many bridge between :class:`SKU` and EAV attribute values.

    Each row pins one attribute value (e.g. "Red") to a specific SKU.
    A unique constraint ensures a SKU can hold only one value per attribute.
    """

    __tablename__ = "sku_attribute_values"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skus.id", ondelete="CASCADE"), index=True
    )
    attribute_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attributes.id", ondelete="CASCADE"), index=True
    )
    attribute_value_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attribute_values.id", ondelete="RESTRICT"), index=True
    )

    sku: Mapped[SKU] = relationship("SKU", back_populates="attribute_values")
    attribute: Mapped[Attribute] = relationship("Attribute")
    attribute_value: Mapped[AttributeValue] = relationship("AttributeValue")

    __table_args__ = (
        UniqueConstraint(
            "sku_id", "attribute_id", name="uix_sku_single_attribute_value"
        ),
        Index("ix_sku_attr_val_lookup", "attribute_value_id", "sku_id"),
    )


# ---------------------------------------------------------------------------
# 6. PRODUCT ATTRIBUTE VALUES
# ---------------------------------------------------------------------------


class ProductAttributeValue(Base):
    """Bridge between Product and EAV attribute values.

    Each row assigns one attribute value to a product.
    Unique constraint ensures one value per attribute per product.
    """

    __tablename__ = "product_attribute_values"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    attribute_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attributes.id", ondelete="CASCADE"), index=True
    )
    attribute_value_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attribute_values.id", ondelete="RESTRICT"), index=True
    )

    product: Mapped[Product] = relationship(
        "Product", back_populates="product_attribute_values"
    )
    attribute: Mapped[Attribute] = relationship("Attribute")
    attribute_value: Mapped[AttributeValue] = relationship("AttributeValue")

    __table_args__ = (
        UniqueConstraint(
            "product_id", "attribute_id", name="uix_product_single_attribute_value"
        ),
        Index("ix_product_attr_val_lookup", "attribute_value_id", "product_id"),
    )
