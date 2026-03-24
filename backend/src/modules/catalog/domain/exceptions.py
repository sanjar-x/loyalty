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


class SKUOutOfStockError(ConflictError):
    """Raised when a stock reservation exceeds available inventory."""

    def __init__(self, sku_id: uuid.UUID, requested: int, available: int):
        super().__init__(
            message="Insufficient stock to fulfill the operation.",
            error_code="SKU_OUT_OF_STOCK",
            details={
                "sku_id": str(sku_id),
                "requested_quantity": requested,
                "available_quantity": available,
            },
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


class CannotDeletePublishedProductError(UnprocessableEntityError):
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
        actual_version: int,
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


class LogoFileNotUploadedError(UnprocessableEntityError):
    """Raised when a logo confirmation is attempted but the file is not in S3."""

    def __init__(self, brand_id: uuid.UUID):
        super().__init__(
            message="Logo file has not been uploaded to storage.",
            error_code="LOGO_FILE_NOT_UPLOADED",
            details={"brand_id": str(brand_id)},
        )


class InvalidLogoStateError(UnprocessableEntityError):
    """Raised when a logo FSM transition is attempted from an invalid state."""

    def __init__(self, brand_id: uuid.UUID, current_status: str, expected_status: str):
        super().__init__(
            message=f"Invalid logo state. Current: {current_status}, expected: {expected_status}.",
            error_code="INVALID_LOGO_STATE",
            details={
                "brand_id": str(brand_id),
                "current_status": current_status,
                "expected_status": expected_status,
            },
        )


class InvalidMediaStateError(UnprocessableEntityError):
    """Raised when a media asset FSM transition is invalid."""

    def __init__(
        self, media_id: uuid.UUID, current_status: str | None, expected_status: str
    ) -> None:
        super().__init__(
            message=f"Media {media_id} is in state {current_status}, expected {expected_status}",
            error_code="INVALID_MEDIA_STATE",
            details={
                "media_id": str(media_id),
                "current_status": current_status,
                "expected_status": expected_status,
            },
        )


# ---------------------------------------------------------------------------
# AttributeGroup aggregate exceptions
# ---------------------------------------------------------------------------


class AttributeGroupNotFoundError(NotFoundError):
    """Raised when an attribute group lookup yields no result."""

    def __init__(self, group_id: uuid.UUID | str):
        super().__init__(
            message=f"Attribute group with ID {group_id} not found.",
            error_code="ATTRIBUTE_GROUP_NOT_FOUND",
            details={"group_id": str(group_id)},
        )


class AttributeGroupCodeConflictError(ConflictError):
    """Raised when an attribute group code collides with an existing group."""

    def __init__(self, code: str):
        super().__init__(
            message=f"Attribute group with code '{code}' already exists.",
            error_code="ATTRIBUTE_GROUP_CODE_CONFLICT",
            details={"code": code},
        )


class AttributeGroupHasAttributesError(ConflictError):
    """Raised when attempting to delete a group that still has attributes."""

    def __init__(self, group_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute group that still contains attributes.",
            error_code="ATTRIBUTE_GROUP_HAS_ATTRIBUTES",
            details={"group_id": str(group_id)},
        )


class AttributeGroupCannotDeleteGeneralError(UnprocessableEntityError):
    """Raised when attempting to delete the protected 'general' group."""

    def __init__(self) -> None:
        super().__init__(
            message="The 'general' attribute group cannot be deleted.",
            error_code="ATTRIBUTE_GROUP_CANNOT_DELETE_GENERAL",
            details={"code": "general"},
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


class AttributeDataTypeChangeError(UnprocessableEntityError):
    """Raised when attempting to change an attribute's data type after creation."""

    def __init__(self, attribute_id: uuid.UUID):
        super().__init__(
            message="Cannot change data type of an existing attribute.",
            error_code="ATTRIBUTE_DATA_TYPE_CHANGE_NOT_ALLOWED",
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


# ---------------------------------------------------------------------------
# Media asset exceptions
# ---------------------------------------------------------------------------


class DuplicateMainMediaError(ConflictError):
    """Raised when a MAIN media asset already exists for a product/variant combo."""

    def __init__(self, product_id: uuid.UUID, variant_id: uuid.UUID | None) -> None:
        super().__init__(
            message="A MAIN media asset already exists for this product/variant.",
            error_code="DUPLICATE_MAIN_MEDIA",
            details={
                "product_id": str(product_id),
                "variant_id": str(variant_id) if variant_id else None,
            },
        )


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


# ---------------------------------------------------------------------------
# AttributeFamily exceptions
# ---------------------------------------------------------------------------


class AttributeFamilyNotFoundError(NotFoundError):
    """Raised when an attribute family lookup yields no result."""

    def __init__(self, family_id: uuid.UUID | str):
        super().__init__(
            message=f"Attribute family with ID {family_id} not found.",
            error_code="ATTRIBUTE_FAMILY_NOT_FOUND",
            details={"family_id": str(family_id)},
        )


class AttributeFamilyCodeAlreadyExistsError(ConflictError):
    """Raised when a family code conflicts with an existing one."""

    def __init__(self, code: str):
        super().__init__(
            message=f"Attribute family with code '{code}' already exists.",
            error_code="ATTRIBUTE_FAMILY_CODE_CONFLICT",
            details={"code": code},
        )


class AttributeFamilyHasChildrenError(ConflictError):
    """Raised when attempting to delete a family that has children."""

    def __init__(self, family_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute family: it has child families.",
            error_code="ATTRIBUTE_FAMILY_HAS_CHILDREN",
            details={"family_id": str(family_id)},
        )


class AttributeFamilyHasCategoryReferencesError(ConflictError):
    """Raised when attempting to delete a family referenced by categories."""

    def __init__(self, family_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute family: it is referenced by categories.",
            error_code="ATTRIBUTE_FAMILY_HAS_CATEGORY_REFERENCES",
            details={"family_id": str(family_id)},
        )


class AttributeFamilyParentImmutableError(UnprocessableEntityError):
    """Raised when attempting to change parent_id or level after creation."""

    def __init__(self, family_id: uuid.UUID):
        super().__init__(
            message="Cannot change parent_id or level after family creation.",
            error_code="ATTRIBUTE_FAMILY_PARENT_IMMUTABLE",
            details={"family_id": str(family_id)},
        )


# ---------------------------------------------------------------------------
# FamilyAttributeBinding exceptions
# ---------------------------------------------------------------------------


class FamilyAttributeBindingNotFoundError(NotFoundError):
    """Raised when a family-attribute binding lookup yields no result."""

    def __init__(self, binding_id: uuid.UUID):
        super().__init__(
            message=f"Family attribute binding with ID {binding_id} not found.",
            error_code="FAMILY_ATTRIBUTE_BINDING_NOT_FOUND",
            details={"binding_id": str(binding_id)},
        )


class FamilyAttributeBindingAlreadyExistsError(ConflictError):
    """Raised when a family-attribute binding pair already exists."""

    def __init__(self, family_id: uuid.UUID, attribute_id: uuid.UUID):
        super().__init__(
            message="This attribute is already bound to the family.",
            error_code="FAMILY_ATTRIBUTE_BINDING_ALREADY_EXISTS",
            details={
                "family_id": str(family_id),
                "attribute_id": str(attribute_id),
            },
        )


# ---------------------------------------------------------------------------
# FamilyAttributeExclusion exceptions
# ---------------------------------------------------------------------------


class FamilyAttributeExclusionNotFoundError(NotFoundError):
    """Raised when a family attribute exclusion lookup yields no result."""

    def __init__(self, exclusion_id: uuid.UUID):
        super().__init__(
            message=f"Family attribute exclusion with ID {exclusion_id} not found.",
            error_code="FAMILY_ATTRIBUTE_EXCLUSION_NOT_FOUND",
            details={"exclusion_id": str(exclusion_id)},
        )


class AttributeNotInheritedError(ValidationError):
    """Raised when trying to exclude an attribute not inherited from ancestors."""

    def __init__(self, family_id: uuid.UUID, attribute_id: uuid.UUID):
        super().__init__(
            message="Cannot exclude: attribute is not inherited from any ancestor family.",
            error_code="ATTRIBUTE_NOT_INHERITED",
            details={
                "family_id": str(family_id),
                "attribute_id": str(attribute_id),
            },
        )


class FamilyExclusionConflictsWithOwnBindingError(ConflictError):
    """Raised when trying to exclude an attribute that has a direct binding on the same family."""

    def __init__(self, family_id: uuid.UUID, attribute_id: uuid.UUID):
        super().__init__(
            message="Cannot exclude: attribute has a direct binding on this family. Remove the binding first.",
            error_code="FAMILY_EXCLUSION_CONFLICTS_WITH_OWN_BINDING",
            details={
                "family_id": str(family_id),
                "attribute_id": str(attribute_id),
            },
        )


class AttributeHasFamilyBindingsError(ConflictError):
    """Raised when attempting to delete an attribute bound to families."""

    def __init__(self, attribute_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute: it is bound to one or more attribute families.",
            error_code="ATTRIBUTE_HAS_FAMILY_BINDINGS",
            details={"attribute_id": str(attribute_id)},
        )
