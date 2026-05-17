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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class BrandUpdatedEvent(
    CatalogEvent,
    required_fields=("brand_id",),
    aggregate_id_field="brand_id",
):
    """Emitted when a brand is updated."""

    brand_id: uuid.UUID | None = None
    aggregate_type: str = "Brand"
    event_type: str = "BrandUpdatedEvent"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class CategoryUpdatedEvent(
    CatalogEvent,
    required_fields=("category_id",),
    aggregate_id_field="category_id",
):
    """Emitted when a category is updated."""

    category_id: uuid.UUID | None = None
    aggregate_type: str = "Category"
    event_type: str = "CategoryUpdatedEvent"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class AttributeTemplateUpdatedEvent(
    CatalogEvent,
    required_fields=("template_id",),
    aggregate_id_field="template_id",
):
    """Emitted when an attribute template is updated."""

    template_id: uuid.UUID | None = None
    aggregate_type: str = "AttributeTemplate"
    event_type: str = "AttributeTemplateUpdatedEvent"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class TemplateAttributeBindingUpdatedEvent(
    CatalogEvent,
    required_fields=("binding_id",),
    aggregate_id_field="binding_id",
):
    """Emitted when a template-attribute binding is updated."""

    binding_id: uuid.UUID | None = None
    aggregate_type: str = "TemplateAttributeBinding"
    event_type: str = "TemplateAttributeBindingUpdatedEvent"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class ProductUpdatedEvent(
    CatalogEvent,
    required_fields=("product_id",),
    aggregate_id_field="product_id",
):
    """Emitted when product fields are updated via partial update."""

    product_id: uuid.UUID | None = None
    aggregate_type: str = "Product"
    event_type: str = "ProductUpdatedEvent"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class MediaAssetAttachedEvent(
    CatalogEvent,
    required_fields=("product_id", "media_asset_id"),
    aggregate_id_field="product_id",
):
    """Emitted when a media asset is added to a product.

    Audit signal for downstream subscribers (analytics, search reindex,
    moderation queue). Companion event to
    :class:`MediaAssetDetachedEvent` — together they form the lifecycle
    pair around the ``media_assets`` table.

    ``storage_object_id`` is optional because external-URL imports
    (``is_external=True``) attach a media row without a backing S3
    object.
    """

    product_id: uuid.UUID | None = None
    media_asset_id: uuid.UUID | None = None
    storage_object_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    role: str = ""
    is_external: bool = False
    aggregate_type: str = "Product"
    event_type: str = "MediaAssetAttachedEvent"


@dataclass(frozen=True)
class MediaAssetDetachedEvent(
    CatalogEvent,
    required_fields=("product_id", "storage_object_id"),
    aggregate_id_field="product_id",
):
    """Emitted when a media asset is removed from a product (IMG-005).

    Carries the underlying ``storage_object_id`` so the image module
    can drop the S3 keys + DB row in a separate transaction.
    Atomicity: this event is written to the outbox in the same UoW as
    the catalog ``DELETE FROM media_assets`` row, so a failed commit
    discards both. Cleanup happens via TaskIQ after the catalog write
    succeeds — orphan-free even on worker crashes (relay retries).
    Replaces the prior best-effort post-commit ``media_cleanup.delete``
    loop in ``UpdateProductHandler``.
    """

    product_id: uuid.UUID | None = None
    storage_object_id: uuid.UUID | None = None
    aggregate_type: str = "Product"
    event_type: str = "MediaAssetDetachedEvent"


@dataclass(frozen=True)
class MediaAssetUpdatedEvent(
    CatalogEvent,
    required_fields=("product_id", "media_asset_id"),
    aggregate_id_field="product_id",
):
    """Emitted when an existing media asset's metadata changes.

    Covers PATCH-style mutations on ``media_assets`` rows that don't
    create or delete the row itself: role, variant binding, and
    sort_order. Carries enough state for downstream subscribers
    (search reindex, audit log, PDP cache invalidation) to react
    without re-reading the row. ``previous_role`` / ``previous_variant_id``
    let auditors reconstruct the change without joining against history.
    """

    product_id: uuid.UUID | None = None
    media_asset_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    previous_variant_id: uuid.UUID | None = None
    role: str = ""
    previous_role: str = ""
    sort_order: int | None = None
    aggregate_type: str = "Product"
    event_type: str = "MediaAssetUpdatedEvent"


# ---------------------------------------------------------------------------
# ProductVariant events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class AttributeGroupUpdatedEvent(
    CatalogEvent,
    required_fields=("group_id",),
    aggregate_id_field="group_id",
):
    """Emitted when an attribute group is updated."""

    group_id: uuid.UUID | None = None
    aggregate_type: str = "AttributeGroup"
    event_type: str = "AttributeGroupUpdatedEvent"


@dataclass(frozen=True)
class AttributeGroupDeletedEvent(
    CatalogEvent,
    required_fields=("group_id",),
    aggregate_id_field="group_id",
):
    """Emitted when an attribute group is deleted."""

    group_id: uuid.UUID | None = None
    aggregate_type: str = "AttributeGroup"
    event_type: str = "AttributeGroupDeletedEvent"
