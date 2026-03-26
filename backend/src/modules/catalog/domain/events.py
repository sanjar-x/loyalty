"""
Catalog domain events.

Events are emitted by Brand, Category, Attribute,
and AttributeTemplate aggregates during business operations, serialized to JSON via
``dataclasses.asdict()``, and stored atomically in the Outbox table.
The infrastructure layer relays them to downstream consumers.

Event Audit (2026-03-26):
- 27 concrete events defined, 27 emitted (by command handlers or domain entities)
- Brand (3): Created / Updated / Deleted
- Category (3): Created / Updated / Deleted
- Attribute (3): Created / Updated / Deleted
- AttributeValue (4): Added / Updated / Deleted / Reordered
- AttributeTemplate (3): Created / Updated / Deleted
- TemplateAttributeBinding (3): Created / Updated / Deleted
- Product (4): Created / StatusChanged / Updated / Deleted  (emitted from domain entity)
- Variant (2): Added / Deleted  (emitted from domain entity)
- SKU (2): Added / Deleted  (emitted from domain entity)
- 0 relay/subscription handlers wired (catalog events are recorded to Outbox
  but no consumer processes them yet — will be wired for ES sync)

Typical usage:
    brand.add_domain_event(BrandLogoUploadInitiatedEvent(brand_id=brand.id, ...))

Note:
    Events are plain (non-frozen) dataclasses because ``DomainEvent``
    (the shared base class) is non-frozen and Python prohibits frozen
    subclasses of non-frozen parents. Events MUST be treated as
    immutable after construction — do not mutate event fields after
    ``__post_init__`` has run.
"""

import uuid
from dataclasses import dataclass
from typing import ClassVar

from src.shared.interfaces.entities import DomainEvent


@dataclass
class CatalogEvent(DomainEvent):
    """Intermediate base for all catalog domain events.

    Subclasses declare which UUID fields are required and which field
    supplies the ``aggregate_id`` via two class-level tuples:

    * ``_required_fields`` — field names that must not be ``None``.
    * ``_aggregate_id_field`` — the single field whose ``str()`` value
      is copied into ``aggregate_id`` when the caller does not set it
      explicitly.

    This eliminates the repetitive ``__post_init__`` boilerplate that
    was previously copy-pasted across every concrete event class.
    """

    # ClassVar so dataclasses ignores them; subclasses override via __init_subclass__
    _required_fields: ClassVar[tuple[str, ...]] = ()
    _aggregate_id_field: ClassVar[str] = ""

    # Provide non-empty defaults so DomainEvent.__init_subclass__ doesn't
    # reject CatalogEvent itself (concrete events override these).
    aggregate_type: str = "Catalog"
    event_type: str = "CatalogEvent"

    def __init_subclass__(
        cls,
        *,
        required_fields: tuple[str, ...] | None = None,
        aggregate_id_field: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(**kwargs)
        if required_fields is not None:
            cls._required_fields = required_fields
        if aggregate_id_field is not None:
            cls._aggregate_id_field = aggregate_id_field

        # Guard: concrete events must override event_type and aggregate_type.
        # Without this, a forgotten override silently inherits "CatalogEvent",
        # causing misrouted events in downstream consumers.
        if required_fields is not None:
            if cls.event_type == "CatalogEvent":
                raise TypeError(
                    f"{cls.__name__} must define its own 'event_type' "
                    f"(inherited default 'CatalogEvent' would misroute events)"
                )
            if cls.aggregate_type == "Catalog":
                raise TypeError(
                    f"{cls.__name__} must define its own 'aggregate_type' "
                    f"(inherited default 'Catalog' would misroute events)"
                )

    def __post_init__(self) -> None:
        cls_name = type(self).__name__
        for field_name in self._required_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required for {cls_name}")
        if not self.aggregate_id and self._aggregate_id_field:
            self.aggregate_id = str(getattr(self, self._aggregate_id_field))


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
