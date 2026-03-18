"""
Catalog domain exceptions.

Each exception maps to a specific business-rule violation within the
Catalog bounded context. The presentation layer translates these into
HTTP error responses via the global exception handler.
"""

import uuid

from src.shared.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
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


class InvalidLogoStateException(UnprocessableEntityError):
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


class AttributeHasCategoryBindingsError(ConflictError):
    """Raised when attempting to delete an attribute bound to categories."""

    def __init__(self, attribute_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute that is bound to one or more categories.",
            error_code="ATTRIBUTE_HAS_CATEGORY_BINDINGS",
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
