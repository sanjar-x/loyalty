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
