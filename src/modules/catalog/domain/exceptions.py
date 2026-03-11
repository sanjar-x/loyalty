# src/modules/catalog/domain/exceptions.py
import uuid

# Импортируем ваши базовые классы (предположим, они лежат в src.shared.exceptions)
from src.shared.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
)

# ==========================================
# CATEGORY AGGREGATE EXCEPTIONS
# ==========================================


class CategoryNotFoundError(NotFoundError):
    def __init__(self, category_id: uuid.UUID | str):
        super().__init__(
            message=f"Категория с ID {category_id} не найдена.",
            error_code="CATEGORY_NOT_FOUND",
            details={"category_id": str(category_id)},
        )


class CategorySlugConflictError(ConflictError):
    def __init__(self, slug: str, parent_id: uuid.UUID | None):
        super().__init__(
            message=f"Категория с URL '{slug}' уже существует на этом уровне.",
            error_code="CATEGORY_SLUG_CONFLICT",
            details={"slug": slug, "parent_id": str(parent_id) if parent_id else None},
        )


class CategoryMaxDepthError(UnprocessableEntityError):
    def __init__(self, max_depth: int, current_level: int):
        super().__init__(
            message=f"Достигнута максимальная глубина дерева ({max_depth}).",
            error_code="CATEGORY_MAX_DEPTH_REACHED",
            details={"max_depth": max_depth, "current_level": current_level},
        )


# ==========================================
# PRODUCT & SKU AGGREGATE EXCEPTIONS
# ==========================================


class ProductNotFoundError(NotFoundError):
    def __init__(self, product_id: uuid.UUID | str):
        super().__init__(
            message=f"Товар с ID {product_id} не найден.",
            error_code="PRODUCT_NOT_FOUND",
            details={"product_id": str(product_id)},
        )


class SKUOutOfStockError(ConflictError):
    def __init__(self, sku_id: uuid.UUID, requested: int, available: int):
        super().__init__(
            message="Недостаточно товара на складе для выполнения операции.",
            error_code="SKU_OUT_OF_STOCK",
            details={
                "sku_id": str(sku_id),
                "requested_quantity": requested,
                "available_quantity": available,
            },
        )


# ==========================================
# BRAND AGGREGATE EXCEPTIONS
# ==========================================


class BrandNotFoundError(NotFoundError):
    def __init__(self, brand_id: uuid.UUID | str):
        super().__init__(
            message=f"Бренд с ID {brand_id} не найден.",
            error_code="BRAND_NOT_FOUND",
            details={"brand_id": str(brand_id)},
        )


class BrandSlugConflictError(ConflictError):
    def __init__(self, slug: str):
        super().__init__(
            message=f"Бренд с URL-идентификатором '{slug}' уже существует.",
            error_code="BRAND_SLUG_CONFLICT",
            details={"slug": slug},
        )
