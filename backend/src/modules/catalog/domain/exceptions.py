"""
Catalog domain exceptions.

Each exception maps to a specific business-rule violation within the
Catalog bounded context. The presentation layer translates these into
HTTP error responses via the global exception handler.
"""

import uuid

from src.modules.catalog.domain.value_objects import ProductStatus
from src.shared.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
    ValidationError,
)

# ---------------------------------------------------------------------------
# Category aggregate exceptions
# ---------------------------------------------------------------------------


class CategoryNotFoundError(NotFoundError):
    """Raised when a category lookup yields no result."""

    def __init__(self, category_id: uuid.UUID | str):
        super().__init__(
            message=f"Category with ID {category_id} not found.",
            error_code="CATEGORY_NOT_FOUND",
            details={"category_id": str(category_id)},
        )


class CategorySlugConflictError(ConflictError):
    """Raised when a category slug collides at the same parent level."""

    def __init__(self, slug: str, parent_id: uuid.UUID | None):
        super().__init__(
            message=f"Category with slug '{slug}' already exists at this level.",
            error_code="CATEGORY_SLUG_CONFLICT",
            details={"slug": slug, "parent_id": str(parent_id) if parent_id else None},
        )


class CategoryMaxDepthError(UnprocessableEntityError):
    """Raised when creating a child would exceed the maximum tree depth."""

    def __init__(self, max_depth: int, current_level: int):
        super().__init__(
            message=f"Maximum category tree depth ({max_depth}) reached.",
            error_code="CATEGORY_MAX_DEPTH_REACHED",
            details={"max_depth": max_depth, "current_level": current_level},
        )


class CategoryHasChildrenError(ConflictError):
    """Raised when attempting to delete a category that still has children."""

    def __init__(self, category_id: uuid.UUID):
        super().__init__(
            message="Cannot delete a category that has child categories.",
            error_code="CATEGORY_HAS_CHILDREN",
            details={"category_id": str(category_id)},
        )


class CategoryHasProductsError(ConflictError):
    """Raised when attempting to delete a category that still has products."""

    def __init__(self, category_id: uuid.UUID):
        super().__init__(
            message="Cannot delete a category that has associated products.",
            error_code="CATEGORY_HAS_PRODUCTS",
            details={"category_id": str(category_id)},
        )


# ---------------------------------------------------------------------------
# Product & SKU aggregate exceptions
# ---------------------------------------------------------------------------


class ProductNotFoundError(NotFoundError):
    """Raised when a product lookup yields no result."""

    def __init__(self, product_id: uuid.UUID | str):
        super().__init__(
            message=f"Product with ID {product_id} not found.",
            error_code="PRODUCT_NOT_FOUND",
            details={"product_id": str(product_id)},
        )


class InvalidStatusTransitionError(UnprocessableEntityError):
    """Raised when a product status transition violates the FSM rules.

    Args:
        current_status: The product's current status at the time of the
            attempted transition.
        target_status: The requested target status that is not allowed.
        allowed_transitions: The list of valid target statuses from the
            current status.
    """

    def __init__(
        self,
        current_status: ProductStatus,
        target_status: ProductStatus,
        allowed_transitions: list[ProductStatus],
    ) -> None:
        super().__init__(
            message=(
                f"Cannot transition from '{current_status.value}' to '{target_status.value}'."
            ),
            error_code="INVALID_STATUS_TRANSITION",
            details={
                "current_status": current_status.value,
                "target_status": target_status.value,
                "allowed_transitions": [s.value for s in allowed_transitions],
            },
        )


class ProductSlugConflictError(ConflictError):
    """Raised when a product slug collides with an existing product.

    Args:
        slug: The slug value that caused the conflict.
    """

    def __init__(self, slug: str) -> None:
        super().__init__(
            message=f"Product with slug '{slug}' already exists.",
            error_code="PRODUCT_SLUG_CONFLICT",
            details={"slug": slug},
        )


class SKUNotFoundError(NotFoundError):
    """Raised when a SKU lookup within a product yields no result.

    Args:
        sku_id: The SKU identifier that was not found.
    """

    def __init__(self, sku_id: uuid.UUID | str) -> None:
        super().__init__(
            message=f"SKU with ID {sku_id} not found.",
            error_code="SKU_NOT_FOUND",
            details={"sku_id": str(sku_id)},
        )


class SKUCodeConflictError(ConflictError):
    """Raised when a SKU code collides within the same product.

    Args:
        sku_code: The SKU code that caused the conflict.
        product_id: The product that already owns a SKU with this code.
    """

    def __init__(self, sku_code: str, product_id: uuid.UUID) -> None:
        super().__init__(
            message=f"SKU with code '{sku_code}' already exists for this product.",
            error_code="SKU_CODE_CONFLICT",
            details={"sku_code": sku_code, "product_id": str(product_id)},
        )


class CannotDeletePublishedProductError(ConflictError):
    """Raised when attempting to delete a product that is currently published."""

    def __init__(self, product_id: uuid.UUID, current_status: str) -> None:
        super().__init__(
            message="Cannot delete a published product. Archive it first.",
            error_code="CANNOT_DELETE_PUBLISHED_PRODUCT",
            details={"product_id": str(product_id), "current_status": current_status},
        )


class ProductNotReadyError(UnprocessableEntityError):
    """Raised when a product is not ready for the requested status transition."""

    def __init__(self, product_id: uuid.UUID, reason: str) -> None:
        super().__init__(
            message=f"Product {product_id} is not ready: {reason}",
            error_code="PRODUCT_NOT_READY",
            details={"product_id": str(product_id), "reason": reason},
        )


class DuplicateVariantCombinationError(ConflictError):
    """Raised when a new SKU would duplicate an existing variant combination.

    The variant combination is identified by a SHA-256 hash of the sorted
    (attribute_id, attribute_value_id) pairs.

    Args:
        product_id: The product on which the collision occurred.
        variant_hash: The computed SHA-256 hash that collided.
    """

    def __init__(self, product_id: uuid.UUID, variant_hash: str) -> None:
        super().__init__(
            message="A variant with the same attribute combination already exists.",
            error_code="DUPLICATE_VARIANT_COMBINATION",
            details={"product_id": str(product_id), "variant_hash": variant_hash},
        )


class DuplicateProductAttributeError(ConflictError):
    """Raised when an attribute is assigned to a product more than once.

    Args:
        product_id: The product to which the attribute is being assigned.
        attribute_id: The attribute that is already assigned to the product.
    """

    def __init__(self, product_id: uuid.UUID, attribute_id: uuid.UUID) -> None:
        super().__init__(
            message="Attribute is already assigned to this product.",
            error_code="DUPLICATE_PRODUCT_ATTRIBUTE",
            details={"product_id": str(product_id), "attribute_id": str(attribute_id)},
        )


class VariantNotFoundError(NotFoundError):
    """Raised when a product variant lookup yields no result."""

    def __init__(
        self, variant_id: uuid.UUID | str, product_id: uuid.UUID | str | None = None
    ) -> None:
        details: dict[str, str] = {"variant_id": str(variant_id)}
        if product_id is not None:
            details["product_id"] = str(product_id)
        super().__init__(
            message=f"Product variant with ID {variant_id} not found.",
            error_code="VARIANT_NOT_FOUND",
            details=details,
        )


class LastVariantRemovalError(UnprocessableEntityError):
    """Raised when attempting to delete the last active variant from a product."""

    def __init__(self, product_id: uuid.UUID) -> None:
        super().__init__(
            message="Cannot delete the last variant from a product.",
            error_code="LAST_VARIANT_REMOVAL",
            details={"product_id": str(product_id)},
        )


class ProductAttributeValueNotFoundError(NotFoundError):
    """Raised when a product attribute value assignment is not found.

    Args:
        product_id: The product whose attribute value was looked up.
        attribute_id: The attribute whose value was not found on the product.
    """

    def __init__(
        self, product_id: uuid.UUID | str, attribute_id: uuid.UUID | str
    ) -> None:
        super().__init__(
            message="Product attribute value not found.",
            error_code="PRODUCT_ATTRIBUTE_VALUE_NOT_FOUND",
            details={"product_id": str(product_id), "attribute_id": str(attribute_id)},
        )


class ConcurrencyError(ConflictError):
    """Raised when an optimistic locking version mismatch is detected.

    This is typically triggered when the infrastructure layer catches
    ``sqlalchemy.orm.exc.StaleDataError`` during a flush and re-raises it
    as this domain exception.

    Args:
        entity_type: Human-readable entity type name, e.g. ``"Product"`` or
            ``"SKU"``.
        entity_id: The UUID of the entity that has the version mismatch.
        expected_version: The version the caller assumed was current.
        actual_version: The version found in the database at flush time.
    """

    def __init__(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        expected_version: int,
        actual_version: int | None,
    ) -> None:
        super().__init__(
            message=f"Concurrent modification detected for {entity_type} {entity_id}.",
            error_code="CONCURRENCY_ERROR",
            details={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
        )


# ---------------------------------------------------------------------------
# Brand aggregate exceptions
# ---------------------------------------------------------------------------


class BrandNotFoundError(NotFoundError):
    """Raised when a brand lookup yields no result."""

    def __init__(self, brand_id: uuid.UUID | str):
        super().__init__(
            message=f"Brand with ID {brand_id} not found.",
            error_code="BRAND_NOT_FOUND",
            details={"brand_id": str(brand_id)},
        )


class BrandHasProductsError(ConflictError):
    """Raised when attempting to delete a brand that still has products."""

    def __init__(self, brand_id: uuid.UUID):
        super().__init__(
            message="Cannot delete a brand that has associated products.",
            error_code="BRAND_HAS_PRODUCTS",
            details={"brand_id": str(brand_id)},
        )


class BrandSlugConflictError(ConflictError):
    """Raised when a brand slug collides with an existing brand."""

    def __init__(self, slug: str):
        super().__init__(
            message=f"Brand with slug '{slug}' already exists.",
            error_code="BRAND_SLUG_CONFLICT",
            details={"slug": slug},
        )


class BrandNameConflictError(ConflictError):
    """Raised when a brand name collides with an existing brand."""

    def __init__(self, name: str):
        super().__init__(
            message=f"Brand with name '{name}' already exists.",
            error_code="BRAND_NAME_CONFLICT",
            details={"name": name},
        )


# ---------------------------------------------------------------------------
# Attribute aggregate exceptions
# ---------------------------------------------------------------------------


class AttributeNotFoundError(NotFoundError):
    """Raised when an attribute lookup yields no result."""

    def __init__(self, attribute_id: uuid.UUID | str):
        super().__init__(
            message=f"Attribute with ID {attribute_id} not found.",
            error_code="ATTRIBUTE_NOT_FOUND",
            details={"attribute_id": str(attribute_id)},
        )


class AttributeGroupNotFoundError(NotFoundError):
    """Raised when an attribute group lookup yields no result."""

    def __init__(self, group_id: uuid.UUID | str):
        super().__init__(
            message=f"Attribute group with ID {group_id} not found.",
            error_code="ATTRIBUTE_GROUP_NOT_FOUND",
            details={"group_id": str(group_id)},
        )


class AttributeCodeConflictError(ConflictError):
    """Raised when an attribute code collides with an existing attribute."""

    def __init__(self, code: str):
        super().__init__(
            message=f"Attribute with code '{code}' already exists.",
            error_code="ATTRIBUTE_CODE_CONFLICT",
            details={"code": code},
        )


class AttributeSlugConflictError(ConflictError):
    """Raised when an attribute slug collides with an existing attribute."""

    def __init__(self, slug: str):
        super().__init__(
            message=f"Attribute with slug '{slug}' already exists.",
            error_code="ATTRIBUTE_SLUG_CONFLICT",
            details={"slug": slug},
        )


class AttributeInUseByProductsError(ConflictError):
    """Raised when attempting to delete an attribute referenced by products."""

    def __init__(self, attribute_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute that is used by one or more products.",
            error_code="ATTRIBUTE_IN_USE_BY_PRODUCTS",
            details={"attribute_id": str(attribute_id)},
        )


# ---------------------------------------------------------------------------
# AttributeValue exceptions
# ---------------------------------------------------------------------------


class AttributeValueNotFoundError(NotFoundError):
    """Raised when an attribute value lookup yields no result."""

    def __init__(self, value_id: uuid.UUID | str):
        super().__init__(
            message=f"Attribute value with ID {value_id} not found.",
            error_code="ATTRIBUTE_VALUE_NOT_FOUND",
            details={"value_id": str(value_id)},
        )


class AttributeValueCodeConflictError(ConflictError):
    """Raised when a value code collides within the same attribute."""

    def __init__(self, code: str, attribute_id: uuid.UUID):
        super().__init__(
            message=f"Attribute value with code '{code}' already exists for this attribute.",
            error_code="ATTRIBUTE_VALUE_CODE_CONFLICT",
            details={"code": code, "attribute_id": str(attribute_id)},
        )


class AttributeValueSlugConflictError(ConflictError):
    """Raised when a value slug collides within the same attribute."""

    def __init__(self, slug: str, attribute_id: uuid.UUID):
        super().__init__(
            message=f"Attribute value with slug '{slug}' already exists for this attribute.",
            error_code="ATTRIBUTE_VALUE_SLUG_CONFLICT",
            details={"slug": slug, "attribute_id": str(attribute_id)},
        )


class AttributeValueInUseError(ConflictError):
    """Raised when attempting to delete an attribute value referenced by products."""

    def __init__(self, value_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute value that is used by one or more products.",
            error_code="ATTRIBUTE_VALUE_IN_USE",
            details={"value_id": str(value_id)},
        )


class AttributeNotDictionaryError(UnprocessableEntityError):
    """Raised when trying to add values to a non-dictionary attribute."""

    def __init__(self, attribute_id: uuid.UUID):
        super().__init__(
            message="Values can only be added to dictionary attributes (is_dictionary=True).",
            error_code="ATTRIBUTE_NOT_DICTIONARY",
            details={"attribute_id": str(attribute_id)},
        )


class InvalidColorHexError(ValidationError):
    """Raised when a color_swatch attribute value has an invalid hex color."""

    def __init__(self, hex_value: str):
        super().__init__(
            message=f"Invalid hex color format: '{hex_value}'. Expected '#RRGGBB'.",
            error_code="INVALID_COLOR_HEX",
            details={"hex_value": hex_value},
        )


# ---------------------------------------------------------------------------
# Media asset exceptions
# ---------------------------------------------------------------------------


class MediaAssetNotFoundError(NotFoundError):
    """Raised when a media asset lookup yields no result."""

    def __init__(
        self, media_id: uuid.UUID | str, product_id: uuid.UUID | str | None = None
    ):
        details: dict[str, str] = {"media_id": str(media_id)}
        if product_id is not None:
            details["product_id"] = str(product_id)
        super().__init__(
            message=f"Media asset with ID {media_id} not found.",
            error_code="MEDIA_ASSET_NOT_FOUND",
            details=details,
        )


class DuplicateMainMediaError(ConflictError):
    """Raised when a variant already has a MAIN media asset."""

    def __init__(
        self,
        product_id: uuid.UUID | str,
        variant_id: uuid.UUID | str | None = None,
    ):
        scope = f"variant {variant_id}" if variant_id else "product (no variant)"
        details: dict[str, str] = {"product_id": str(product_id)}
        if variant_id is not None:
            details["variant_id"] = str(variant_id)
        super().__init__(
            message=f"A MAIN media asset already exists for {scope}.",
            error_code="DUPLICATE_MAIN_MEDIA",
            details=details,
        )


# ---------------------------------------------------------------------------
# AttributeTemplate exceptions
# ---------------------------------------------------------------------------


class AttributeTemplateNotFoundError(NotFoundError):
    """Raised when an attribute template lookup yields no result."""

    def __init__(self, template_id: uuid.UUID | str):
        super().__init__(
            message=f"Attribute template with ID {template_id} not found.",
            error_code="ATTRIBUTE_TEMPLATE_NOT_FOUND",
            details={"template_id": str(template_id)},
        )


class AttributeTemplateCodeAlreadyExistsError(ConflictError):
    """Raised when a template code conflicts with an existing one."""

    def __init__(self, code: str):
        super().__init__(
            message=f"Attribute template with code '{code}' already exists.",
            error_code="ATTRIBUTE_TEMPLATE_CODE_CONFLICT",
            details={"code": code},
        )


class AttributeTemplateHasCategoryReferencesError(ConflictError):
    """Raised when attempting to delete a template referenced by categories."""

    def __init__(self, template_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute template: it is referenced by categories.",
            error_code="ATTRIBUTE_TEMPLATE_HAS_CATEGORY_REFERENCES",
            details={"template_id": str(template_id)},
        )


# ---------------------------------------------------------------------------
# TemplateAttributeBinding exceptions
# ---------------------------------------------------------------------------


class TemplateAttributeBindingNotFoundError(NotFoundError):
    """Raised when a template-attribute binding lookup yields no result."""

    def __init__(self, binding_id: uuid.UUID):
        super().__init__(
            message=f"Template attribute binding with ID {binding_id} not found.",
            error_code="TEMPLATE_ATTRIBUTE_BINDING_NOT_FOUND",
            details={"binding_id": str(binding_id)},
        )


class TemplateAttributeBindingAlreadyExistsError(ConflictError):
    """Raised when a template-attribute binding pair already exists."""

    def __init__(self, template_id: uuid.UUID, attribute_id: uuid.UUID):
        super().__init__(
            message="This attribute is already bound to the template.",
            error_code="TEMPLATE_ATTRIBUTE_BINDING_ALREADY_EXISTS",
            details={
                "template_id": str(template_id),
                "attribute_id": str(attribute_id),
            },
        )


class AttributeHasTemplateBindingsError(ConflictError):
    """Raised when attempting to delete an attribute bound to templates."""

    def __init__(self, attribute_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute: it is bound to one or more attribute templates.",
            error_code="ATTRIBUTE_HAS_TEMPLATE_BINDINGS",
            details={"attribute_id": str(attribute_id)},
        )


class MissingRequiredLocalesError(ValidationError):
    """Raised when an i18n field is missing one or more required locales."""

    def __init__(self, field_name: str, missing_locales: list[str]):
        super().__init__(
            message=f"{field_name} is missing required locales: {', '.join(missing_locales)}",
            error_code="MISSING_REQUIRED_LOCALES",
            details={"field": field_name, "missing_locales": missing_locales},
        )


class AttributeLevelMismatchError(UnprocessableEntityError):
    """Raised when assigning an attribute at the wrong level (product vs variant)."""

    def __init__(self, attribute_id: uuid.UUID, expected_level: str, actual_level: str):
        super().__init__(
            message=f"Attribute level mismatch: expected '{expected_level}', got '{actual_level}'.",
            error_code="ATTRIBUTE_LEVEL_MISMATCH",
            details={
                "attribute_id": str(attribute_id),
                "expected_level": expected_level,
                "actual_level": actual_level,
            },
        )


class AttributeNotInTemplateError(UnprocessableEntityError):
    """Raised when assigning an attribute not present in the product's category template."""

    def __init__(self, product_id: uuid.UUID, attribute_id: uuid.UUID):
        super().__init__(
            message="Attribute is not in the product's category attribute template.",
            error_code="ATTRIBUTE_NOT_IN_TEMPLATE",
            details={
                "product_id": str(product_id),
                "attribute_id": str(attribute_id),
            },
        )
