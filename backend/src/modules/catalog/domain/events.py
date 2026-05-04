"""Catalog domain events.

Catalog is the only module whose events span **multiple** aggregate kinds
(``Brand``, ``Category``, ``Attribute``, ``AttributeTemplate``,
``AttributeGroup``, ``TemplateAttributeBinding``, ``Product``) within a
single bounded context. Each concrete event therefore MUST override
``aggregate_type`` with the specific aggregate name; the
:class:`CatalogEvent` intermediate base enforces that explicitly.

Required-field validation and ``aggregate_id`` auto-fill come from
:class:`src.shared.interfaces.entities.ModuleDomainEvent`.

Event Audit (2026-03-26):
- 27 concrete events defined, 27 emitted (by command handlers or domain entities)
- Brand (3): Created / Updated / Deleted
- Category (3): Created / Updated / Deleted
- Attribute (3): Created / Updated / Deleted
- AttributeValue (4): Added / Updated / Deleted / Reordered
- AttributeTemplate (3): Created / Updated / Deleted
- TemplateAttributeBinding (3): Created / Updated / Deleted
- Product (4): Created / StatusChanged / Updated / Deleted (from domain entity)
- Variant (2): Added / Deleted (from domain entity)
- SKU (2): Added / Deleted (from domain entity)
"""

import uuid
from dataclasses import dataclass

from src.shared.interfaces.entities import ModuleDomainEvent


@dataclass
class CatalogEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all catalog domain events.

    Catalog spans multiple aggregate kinds, so concrete events MUST
    override ``aggregate_type`` with their specific aggregate name
    (e.g. ``"Brand"``, ``"Category"``, ``"Attribute"``). The validator
    below enforces that on class construction.
    """

    aggregate_type: str = "Catalog"

    def __init_subclass__(
        cls,
        *,
        abstract: bool = False,
        required_fields: tuple[str, ...] | None = None,
        aggregate_id_field: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(
            abstract=abstract,
            required_fields=required_fields,
            aggregate_id_field=aggregate_id_field,
            **kwargs,
        )
        if abstract or required_fields is None:
            return
        if "aggregate_type" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must override 'aggregate_type' — catalog "
                "events span multiple aggregate kinds (Brand, Category, "
                "Attribute, ...) and cannot inherit the placeholder "
                "'Catalog'."
            )


# ---------------------------------------------------------------------------
# Brand events
# ---------------------------------------------------------------------------


@dataclass
class BrandCreatedEvent(
    CatalogEvent,
    required_fields=("brand_id",),
    aggregate_id_field="brand_id",
):
    """Emitted when a new brand is created."""

    brand_id: uuid.UUID | None = None
    slug: str = ""
    aggregate_type: str = "Brand"
    event_type: str = "BrandCreatedEvent"


@dataclass
class BrandUpdatedEvent(
    CatalogEvent,
    required_fields=("brand_id",),
    aggregate_id_field="brand_id",
):
    """Emitted when a brand is updated."""

    brand_id: uuid.UUID | None = None
    aggregate_type: str = "Brand"
    event_type: str = "BrandUpdatedEvent"


@dataclass
class BrandDeletedEvent(
    CatalogEvent,
    required_fields=("brand_id",),
    aggregate_id_field="brand_id",
):
    """Emitted when a brand is deleted."""

    brand_id: uuid.UUID | None = None
    aggregate_type: str = "Brand"
    event_type: str = "BrandDeletedEvent"


# ---------------------------------------------------------------------------
# Category events
# ---------------------------------------------------------------------------


@dataclass
class CategoryCreatedEvent(
    CatalogEvent,
    required_fields=("category_id",),
    aggregate_id_field="category_id",
):
    """Emitted when a new category is created."""

    category_id: uuid.UUID | None = None
    slug: str = ""
    aggregate_type: str = "Category"
    event_type: str = "CategoryCreatedEvent"


@dataclass
class CategoryUpdatedEvent(
    CatalogEvent,
    required_fields=("category_id",),
    aggregate_id_field="category_id",
):
    """Emitted when a category is updated."""

    category_id: uuid.UUID | None = None
    aggregate_type: str = "Category"
    event_type: str = "CategoryUpdatedEvent"


@dataclass
class CategoryDeletedEvent(
    CatalogEvent,
    required_fields=("category_id",),
    aggregate_id_field="category_id",
):
    """Emitted when a category is deleted.

    Downstream consumers (e.g. search index) react by removing
    the category from their stores.
    """

    category_id: uuid.UUID | None = None
    slug: str = ""
    aggregate_type: str = "Category"
    event_type: str = "CategoryDeletedEvent"


# ---------------------------------------------------------------------------
# Attribute events
# ---------------------------------------------------------------------------


@dataclass
class AttributeCreatedEvent(
    CatalogEvent,
    required_fields=("attribute_id",),
    aggregate_id_field="attribute_id",
):
    """Emitted when a new attribute is created.

    Attributes:
        attribute_id: UUID of the newly created attribute.
        code: Machine-readable attribute code.
    """

    attribute_id: uuid.UUID | None = None
    code: str = ""
    aggregate_type: str = "Attribute"
    event_type: str = "AttributeCreatedEvent"


@dataclass
class AttributeUpdatedEvent(
    CatalogEvent,
    required_fields=("attribute_id",),
    aggregate_id_field="attribute_id",
):
    """Emitted when an attribute is updated.

    Attributes:
        attribute_id: UUID of the updated attribute.
    """

    attribute_id: uuid.UUID | None = None
    aggregate_type: str = "Attribute"
    event_type: str = "AttributeUpdatedEvent"


@dataclass
class AttributeDeletedEvent(
    CatalogEvent,
    required_fields=("attribute_id",),
    aggregate_id_field="attribute_id",
):
    """Emitted when an attribute is deleted.

    Attributes:
        attribute_id: UUID of the deleted attribute.
        code: Code of the deleted attribute.
    """

    attribute_id: uuid.UUID | None = None
    code: str = ""
    aggregate_type: str = "Attribute"
    event_type: str = "AttributeDeletedEvent"


# ---------------------------------------------------------------------------
# AttributeValue events
# ---------------------------------------------------------------------------


@dataclass
class AttributeValueAddedEvent(
    CatalogEvent,
    required_fields=("attribute_id", "value_id"),
    aggregate_id_field="attribute_id",
):
    """Emitted when a new value is added to a dictionary attribute.

    Attributes:
        attribute_id: UUID of the parent attribute.
        value_id: UUID of the newly added value.
        code: Machine-readable value code.
    """

    attribute_id: uuid.UUID | None = None
    value_id: uuid.UUID | None = None
    code: str = ""
    aggregate_type: str = "Attribute"
    event_type: str = "AttributeValueAddedEvent"


@dataclass
class AttributeValueUpdatedEvent(
    CatalogEvent,
    required_fields=("attribute_id", "value_id"),
    aggregate_id_field="attribute_id",
):
    """Emitted when an attribute value is updated.

    Attributes:
        attribute_id: UUID of the parent attribute.
        value_id: UUID of the updated value.
    """

    attribute_id: uuid.UUID | None = None
    value_id: uuid.UUID | None = None
    aggregate_type: str = "Attribute"
    event_type: str = "AttributeValueUpdatedEvent"


@dataclass
class AttributeValueDeletedEvent(
    CatalogEvent,
    required_fields=("attribute_id", "value_id"),
    aggregate_id_field="attribute_id",
):
    """Emitted when an attribute value is deleted.

    Attributes:
        attribute_id: UUID of the parent attribute.
        value_id: UUID of the deleted value.
        code: Code of the deleted value.
    """

    attribute_id: uuid.UUID | None = None
    value_id: uuid.UUID | None = None
    code: str = ""
    aggregate_type: str = "Attribute"
    event_type: str = "AttributeValueDeletedEvent"


@dataclass
class AttributeValuesReorderedEvent(
    CatalogEvent,
    required_fields=("attribute_id",),
    aggregate_id_field="attribute_id",
):
    """Emitted when attribute values are bulk-reordered."""

    attribute_id: uuid.UUID | None = None
    aggregate_type: str = "Attribute"
    event_type: str = "AttributeValuesReorderedEvent"


# ---------------------------------------------------------------------------
# AttributeTemplate events
# ---------------------------------------------------------------------------


@dataclass
class AttributeTemplateCreatedEvent(
    CatalogEvent,
    required_fields=("template_id",),
    aggregate_id_field="template_id",
):
    """Emitted when a new attribute template is created."""

    template_id: uuid.UUID | None = None
    code: str = ""
    aggregate_type: str = "AttributeTemplate"
    event_type: str = "AttributeTemplateCreatedEvent"


@dataclass
class AttributeTemplateUpdatedEvent(
    CatalogEvent,
    required_fields=("template_id",),
    aggregate_id_field="template_id",
):
    """Emitted when an attribute template is updated."""

    template_id: uuid.UUID | None = None
    aggregate_type: str = "AttributeTemplate"
    event_type: str = "AttributeTemplateUpdatedEvent"


@dataclass
class AttributeTemplateDeletedEvent(
    CatalogEvent,
    required_fields=("template_id",),
    aggregate_id_field="template_id",
):
    """Emitted when an attribute template is deleted."""

    template_id: uuid.UUID | None = None
    code: str = ""
    aggregate_type: str = "AttributeTemplate"
    event_type: str = "AttributeTemplateDeletedEvent"


# ---------------------------------------------------------------------------
# TemplateAttributeBinding events
# ---------------------------------------------------------------------------


@dataclass
class TemplateAttributeBindingCreatedEvent(
    CatalogEvent,
    required_fields=("binding_id",),
    aggregate_id_field="binding_id",
):
    """Emitted when an attribute is bound to a template."""

    template_id: uuid.UUID | None = None
    attribute_id: uuid.UUID | None = None
    binding_id: uuid.UUID | None = None
    aggregate_type: str = "TemplateAttributeBinding"
    event_type: str = "TemplateAttributeBindingCreatedEvent"


@dataclass
class TemplateAttributeBindingUpdatedEvent(
    CatalogEvent,
    required_fields=("binding_id",),
    aggregate_id_field="binding_id",
):
    """Emitted when a template-attribute binding is updated."""

    binding_id: uuid.UUID | None = None
    aggregate_type: str = "TemplateAttributeBinding"
    event_type: str = "TemplateAttributeBindingUpdatedEvent"


@dataclass
class TemplateAttributeBindingDeletedEvent(
    CatalogEvent,
    required_fields=("binding_id",),
    aggregate_id_field="binding_id",
):
    """Emitted when an attribute is unbound from a template."""

    template_id: uuid.UUID | None = None
    attribute_id: uuid.UUID | None = None
    binding_id: uuid.UUID | None = None
    aggregate_type: str = "TemplateAttributeBinding"
    event_type: str = "TemplateAttributeBindingDeletedEvent"


# ---------------------------------------------------------------------------
# Product events
# ---------------------------------------------------------------------------


@dataclass
class ProductCreatedEvent(
    CatalogEvent,
    required_fields=("product_id",),
    aggregate_id_field="product_id",
):
    """Emitted when a new product is created."""

    product_id: uuid.UUID | None = None
    slug: str = ""
    aggregate_type: str = "Product"
    event_type: str = "ProductCreatedEvent"


@dataclass
class ProductStatusChangedEvent(
    CatalogEvent,
    required_fields=("product_id",),
    aggregate_id_field="product_id",
):
    """Emitted when a product's status transitions."""

    product_id: uuid.UUID | None = None
    old_status: str = ""
    new_status: str = ""
    aggregate_type: str = "Product"
    event_type: str = "ProductStatusChangedEvent"


@dataclass
class ProductUpdatedEvent(
    CatalogEvent,
    required_fields=("product_id",),
    aggregate_id_field="product_id",
):
    """Emitted when product fields are updated via partial update."""

    product_id: uuid.UUID | None = None
    aggregate_type: str = "Product"
    event_type: str = "ProductUpdatedEvent"


@dataclass
class ProductDeletedEvent(
    CatalogEvent,
    required_fields=("product_id",),
    aggregate_id_field="product_id",
):
    """Emitted when a product is soft-deleted."""

    product_id: uuid.UUID | None = None
    slug: str = ""
    aggregate_type: str = "Product"
    event_type: str = "ProductDeletedEvent"


# ---------------------------------------------------------------------------
# ProductVariant events
# ---------------------------------------------------------------------------


@dataclass
class VariantAddedEvent(
    CatalogEvent,
    required_fields=("product_id", "variant_id"),
    aggregate_id_field="product_id",
):
    """Emitted when a new variant is added to a product."""

    product_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    aggregate_type: str = "Product"
    event_type: str = "VariantAddedEvent"


@dataclass
class VariantDeletedEvent(
    CatalogEvent,
    required_fields=("product_id", "variant_id"),
    aggregate_id_field="product_id",
):
    """Emitted when a variant is soft-deleted from a product."""

    product_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    aggregate_type: str = "Product"
    event_type: str = "VariantDeletedEvent"


# ---------------------------------------------------------------------------
# SKU events
# ---------------------------------------------------------------------------


@dataclass
class SKUAddedEvent(
    CatalogEvent,
    required_fields=("product_id", "variant_id", "sku_id"),
    aggregate_id_field="product_id",
):
    """Emitted when a new SKU is added to a product variant."""

    product_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    sku_id: uuid.UUID | None = None
    aggregate_type: str = "Product"
    event_type: str = "SKUAddedEvent"


@dataclass
class SKUDeletedEvent(
    CatalogEvent,
    required_fields=("product_id", "variant_id", "sku_id"),
    aggregate_id_field="product_id",
):
    """Emitted when a SKU is soft-deleted from a product variant."""

    product_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    sku_id: uuid.UUID | None = None
    aggregate_type: str = "Product"
    event_type: str = "SKUDeletedEvent"


# ---------------------------------------------------------------------------
# SKU pricing events (ADR-005)
# ---------------------------------------------------------------------------
# These events drive the autonomous recompute pipeline. They carry
# ``sku_id`` as a top-level payload field so the outbox handler can
# enqueue a per-SKU TaskIQ job without re-reading the SKU row.


@dataclass
class SKUPurchasePriceUpdatedEvent(
    CatalogEvent,
    required_fields=("product_id", "sku_id", "purchase_currency"),
    aggregate_id_field="product_id",
):
    """Emitted when a SKU's purchase price or purchase currency changes.

    Triggers an asynchronous recompute of the SKU's selling price via
    the pricing recompute pipeline (see ADR-005). The payload carries
    the *new* values formatted as strings to keep the JSON envelope
    schema-stable; consumers re-read the SKU row inside their own
    transaction before computing.
    """

    product_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    sku_id: uuid.UUID | None = None
    purchase_price_amount: int | None = None
    purchase_currency: str | None = None
    aggregate_type: str = "Product"
    event_type: str = "SKUPurchasePriceUpdatedEvent"


@dataclass
class SKUPricedEvent(
    CatalogEvent,
    required_fields=("product_id", "sku_id", "selling_price_amount"),
    aggregate_id_field="product_id",
):
    """Emitted when a SKU transitions to a fresh PRICED state."""

    product_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    sku_id: uuid.UUID | None = None
    selling_price_amount: int | None = None
    selling_currency: str | None = None
    formula_version_id: uuid.UUID | None = None
    inputs_hash: str | None = None
    aggregate_type: str = "Product"
    event_type: str = "SKUPricedEvent"


@dataclass
class SKUPricingFailedEvent(
    CatalogEvent,
    required_fields=("product_id", "sku_id", "pricing_status", "failure_reason"),
    aggregate_id_field="product_id",
):
    """Emitted when a recompute attempt cannot produce a valid selling price.

    ``pricing_status`` is one of ``stale_fx`` / ``missing_purchase_price``
    / ``formula_error``; ``failure_reason`` carries a short admin-
    readable message for surfacing in the back office.
    """

    product_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    sku_id: uuid.UUID | None = None
    pricing_status: str | None = None
    failure_reason: str | None = None
    aggregate_type: str = "Product"
    event_type: str = "SKUPricingFailedEvent"


# ---------------------------------------------------------------------------
# AttributeGroup events
# ---------------------------------------------------------------------------


@dataclass
class AttributeGroupCreatedEvent(
    CatalogEvent,
    required_fields=("group_id",),
    aggregate_id_field="group_id",
):
    """Emitted when a new attribute group is created."""

    group_id: uuid.UUID | None = None
    code: str = ""
    aggregate_type: str = "AttributeGroup"
    event_type: str = "AttributeGroupCreatedEvent"


@dataclass
class AttributeGroupUpdatedEvent(
    CatalogEvent,
    required_fields=("group_id",),
    aggregate_id_field="group_id",
):
    """Emitted when an attribute group is updated."""

    group_id: uuid.UUID | None = None
    aggregate_type: str = "AttributeGroup"
    event_type: str = "AttributeGroupUpdatedEvent"


@dataclass
class AttributeGroupDeletedEvent(
    CatalogEvent,
    required_fields=("group_id",),
    aggregate_id_field="group_id",
):
    """Emitted when an attribute group is deleted."""

    group_id: uuid.UUID | None = None
    aggregate_type: str = "AttributeGroup"
    event_type: str = "AttributeGroupDeletedEvent"
