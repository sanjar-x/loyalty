# src/modules/catalog/infrastructure/models.py
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    TIMESTAMP,
    Boolean,
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
from src.modules.catalog.domain.value_objects import MediaProcessingStatus


class AttributeDataType(enum.StrEnum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"


class AttributeUIType(enum.StrEnum):
    TEXT_BUTTON = "text_button"
    COLOR_SWATCH = "color_swatch"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RANGE_SLIDER = "range_slider"


class ProductStatus(enum.StrEnum):
    DRAFT = "draft"
    ENRICHING = "enriching"
    READY_FOR_REVIEW = "ready_for_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"



class MediaType(enum.StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    MODEL_3D = "model_3d"
    DOCUMENT = "document"


class MediaRole(enum.StrEnum):
    MAIN = "main"
    HOVER = "hover"
    GALLERY = "gallery"
    HERO_VIDEO = "hero_video"
    SIZE_GUIDE = "size_guide"
    PACKAGING = "packaging"


class SupplierType(enum.StrEnum):
    CROSS_BORDER = "cross_border"
    LOCAL = "local"


# ==========================================
# 2. TAXONOMY & DICTIONARIES (СПРАВОЧНИКИ)
# ==========================================


class Brand(Base):
    """Модель бренда для группировки товаров (например, Nike, Adidas)."""

    __tablename__ = "brands"
    __table_args__ = (
        Index("uix_brands_name", "name", unique=True),
        {"comment": "Справочник брендов каталога"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        comment="Первичный ключ (UUIDv7 для сортировки по времени)",
    )

    name: Mapped[str] = mapped_column(String(255), comment="Название бренда")
    slug: Mapped[str] = mapped_column(
        String(255), index=True, comment="URL-идентификатор для роутинга"
    )
    logo_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Soft-link на storage_objects.id (Модуль Storage)",
    )

    logo_status: Mapped[MediaProcessingStatus | None] = mapped_column(
        Enum(MediaProcessingStatus, native_enum=False, length=30),
        nullable=True,
        comment="FSM: Текущий этап загрузки/обработки логотипа",
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Кэш публичного URL из модуля Storage",
    )
    logo_draft_key: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Временный путь в S3 (до создания StorageObject воркером)",
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    full_slug: Mapped[str] = mapped_column(String(1000), index=True)
    level: Mapped[int] = mapped_column(Integer, server_default=text("0"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), index=True
    )

    children: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped["Category"] = relationship(
        "Category", back_populates="children", remote_side="Category.id"
    )
    attribute_rules: Mapped[list["CategoryAttributeRule"]] = relationship(
        "CategoryAttributeRule", back_populates="category", cascade="all, delete-orphan"
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


class Attribute(Base):
    __tablename__ = "attributes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7, comment="ID (UUIDv7)"
    )
    code: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(255))

    name_i18n: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(sqltype=JSONB), server_default=text("'{}'::jsonb")
    )
    description_i18n: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(sqltype=JSONB), server_default=text("'{}'::jsonb")
    )
    data_type: Mapped[AttributeDataType] = mapped_column(
        Enum(AttributeDataType, name="attribute_data_type_enum"),
        server_default=AttributeDataType.STRING.name,
    )
    ui_type: Mapped[AttributeUIType] = mapped_column(
        Enum(AttributeUIType, name="attribute_ui_type_enum"),
        server_default=AttributeUIType.TEXT_BUTTON.name,
    )
    is_dictionary: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    values: Mapped[list["AttributeValue"]] = relationship(
        "AttributeValue", back_populates="attribute", cascade="all, delete-orphan"
    )
    category_rules: Mapped[list["CategoryAttributeRule"]] = relationship(
        "CategoryAttributeRule",
        back_populates="attribute",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("uix_attributes_code", "code", unique=True),
        Index("uix_attributes_slug", "slug", unique=True),
        Index("ix_attributes_name_i18n_gin", "name_i18n", postgresql_using="gin"),
    )


class AttributeValue(Base):
    """Справочник конкретных вариантов (Красный, 42, Хлопок)."""

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
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), server_default=text("'{}'::jsonb")
    )
    group_code: Mapped[str | None] = mapped_column(String(100), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    attribute: Mapped["Attribute"] = relationship("Attribute", back_populates="values")

    __table_args__ = (
        Index("uix_attr_val_code", "attribute_id", "code", unique=True),
        Index("uix_attr_val_slug", "attribute_id", "slug", unique=True),
        Index("ix_attr_val_value_i18n_gin", "value_i18n", postgresql_using="gin"),
        Index(
            "ix_attr_val_search_aliases_gin", "search_aliases", postgresql_using="gin"
        ),
    )


# ==========================================
# 3. RULES (ПРАВИЛА И СВЯЗИ)
# ==========================================


class CategoryAttributeRule(Base):
    """Модель Governance: как атрибуты ведут себя в конкретной категории."""

    __tablename__ = "category_attribute_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    attribute_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attributes.id", ondelete="CASCADE"), index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    category: Mapped["Category"] = relationship(
        "Category", back_populates="attribute_rules"
    )
    attribute: Mapped["Attribute"] = relationship(
        "Attribute", back_populates="category_rules"
    )

    __table_args__ = (
        Index("uix_cat_attr_rule", "category_id", "attribute_id", unique=True),
    )


# ==========================================
# 4. CORE DOMAIN (ЯДРО КАТАЛОГА)
# ==========================================


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[SupplierType] = mapped_column(
        Enum(SupplierType, name="supplier_type_enum")
    )
    region: Mapped[str | None] = mapped_column(String(255))
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="supplier"
    )


class Product(Base):
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
    supplier_id: Mapped[uuid.UUID] = mapped_column(
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

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Дата и время создания записи",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), index=True
    )
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="products")
    skus: Mapped[list["SKU"]] = relationship(
        "SKU", back_populates="product", cascade="all, delete-orphan"
    )

    __mapper_args__ = {
        "version_id_col": version,
    }

    __table_args__ = (
        Index(
            "uix_products_slug",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_products_attributes_gin", "attributes", postgresql_using="gin"),
        Index("ix_products_title_gin", "title_i18n", postgresql_using="gin"),
        Index("ix_products_tags_gin", "tags", postgresql_using="gin"),
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


class MediaAsset(Base):
    """
    Сущность: Медиа-актив товара (Бизнес-контекст).
    Описывает, КАК файл используется в каталоге (роль, порядок, привязка к цвету).
    Сами физические данные файла лежат в модуле Storage (StorageObject).
    """

    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    attribute_value_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attribute_values.id", ondelete="CASCADE"), index=True
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

    # Мягкая связь (Soft Link) с модулем Storage
    storage_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        index=True,
        nullable=True,
        comment="Ссылка на storage_objects.id (Единый реестр файлов)",
    )

    is_external: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        comment="Флаг внешнего ресурса (не управляемого нашим S3)",
    )
    external_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Прямая ссылка (например, youtube.com/...), если is_external = true",
    )

    # Навигационные свойства (Relationship)
    product: Mapped["Product"] = relationship(
        "Product"
    )  # или back_populates если добавишь в Product
    color_attribute: Mapped["AttributeValue"] = relationship("AttributeValue")

    __table_args__ = (
        Index("ix_media_assets_product_attr", "product_id", "attribute_value_id"),
        # Бизнес-правило: У одного цвета может быть только одна ГЛАВНАЯ картинка
        Index(
            "uix_media_single_main_per_color",
            "product_id",
            "attribute_value_id",
            unique=True,
            postgresql_where=text("role = 'MAIN'"),
            postgresql_nulls_not_distinct=True,
        ),
    )


# ==========================================
# 5. VARIATIONS (SKU И СВЯЗИ АТРИБУТОВ)
# ==========================================


class SKU(Base):
    __tablename__ = "skus"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    sku_code: Mapped[str] = mapped_column(String(100))
    variant_hash: Mapped[str] = mapped_column(String(64), unique=True)
    main_image_url: Mapped[str | None] = mapped_column(String(1024))
    attributes_cache: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), server_default=text("'{}'::jsonb")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    price: Mapped[int] = mapped_column(
        Integer,
        server_default=text("0"),
        comment="Базовая цена в минимальных единицах валюты",
    )

    compare_at_price: Mapped[int | None] = mapped_column(
        Integer, comment="Старая цена (для зачеркивания)"
    )

    currency: Mapped[str] = mapped_column(String(3), server_default=text("'RUB'"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), index=True
    )

    product: Mapped["Product"] = relationship("Product", back_populates="skus")
    attribute_values: Mapped[list["SKUAttributeValueLink"]] = relationship(
        "SKUAttributeValueLink", back_populates="sku", cascade="all, delete-orphan"
    )

    __mapper_args__ = {
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
    """
    Сущность: Матрица вариаций (M2M мост между SKU и EAV).
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

    sku: Mapped["SKU"] = relationship("SKU", back_populates="attribute_values")
    attribute: Mapped["Attribute"] = relationship("Attribute")
    attribute_value: Mapped["AttributeValue"] = relationship("AttributeValue")

    __table_args__ = (
        UniqueConstraint(
            "sku_id", "attribute_id", name="uix_sku_single_attribute_value"
        ),
        Index("ix_sku_attr_val_lookup", "attribute_value_id", "sku_id"),
    )
