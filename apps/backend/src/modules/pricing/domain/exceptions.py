"""Pricing domain exceptions.

Thin wrappers over ``src.shared.exceptions`` with pricing-specific error codes
and messages. The presentation layer relies on ``AppException`` mapping for
HTTP status codes.
"""

from __future__ import annotations

import uuid
from typing import Any

from src.shared.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
    ValidationError,
)


class ProductPricingProfileNotFoundError(NotFoundError):
    """Raised when a profile for the given product_id does not exist."""

    def __init__(self, product_id: uuid.UUID) -> None:
        super().__init__(
            message=f"Pricing profile for product {product_id} not found.",
            error_code="PRICING_PROFILE_NOT_FOUND",
            details={"product_id": str(product_id)},
        )


class ProductPricingProfileVersionConflictError(ConflictError):
    """Raised on optimistic-lock mismatch during an upsert."""

    def __init__(
        self,
        product_id: uuid.UUID,
        expected_version: int,
        actual_version: int,
    ) -> None:
        super().__init__(
            message=(
                "Pricing profile was modified by another request. "
                f"Expected version {expected_version}, got {actual_version}."
            ),
            error_code="PRICING_PROFILE_VERSION_CONFLICT",
            details={
                "product_id": str(product_id),
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
        )


class PricingProfileValidationError(ValidationError):
    """Raised when the provided profile values fail domain validation."""

    def __init__(
        self,
        message: str,
        error_code: str = "PRICING_PROFILE_INVALID",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


# ---------------------------------------------------------------------------
# Variable registry
# ---------------------------------------------------------------------------


class VariableNotFoundError(NotFoundError):
    """Raised when a variable does not exist (by id or code)."""

    def __init__(
        self,
        *,
        variable_id: uuid.UUID | None = None,
        code: str | None = None,
    ) -> None:
        identifier = (
            f"id={variable_id}" if variable_id is not None else f"code={code!r}"
        )
        super().__init__(
            message=f"Variable not found ({identifier}).",
            error_code="PRICING_VARIABLE_NOT_FOUND",
            details={
                "variable_id": str(variable_id) if variable_id else None,
                "code": code,
            },
        )


class VariableCodeTakenError(ConflictError):
    """Raised when creating a variable with a code that already exists."""

    def __init__(self, code: str) -> None:
        super().__init__(
            message=f"Variable with code {code!r} already exists.",
            error_code="PRICING_VARIABLE_CODE_TAKEN",
            details={"code": code},
        )


class VariableInUseError(ConflictError):
    """Raised when deleting a variable that is referenced elsewhere.

    In v1 only ``ProductPricingProfile.values`` is checked; future slices
    (formulas, category/supplier/range settings) must extend the reference
    check to cover those aggregates too.
    """

    def __init__(
        self,
        *,
        variable_id: uuid.UUID,
        code: str,
        reference_count: int,
        reference_kind: str = "product_pricing_profile_values",
    ) -> None:
        super().__init__(
            message=(
                f"Variable {code!r} is still referenced by "
                f"{reference_count} {reference_kind.replace('_', ' ')}; "
                "remove those references before deleting."
            ),
            error_code="PRICING_VARIABLE_IN_USE",
            details={
                "variable_id": str(variable_id),
                "code": code,
                "reference_count": reference_count,
                "reference_kind": reference_kind,
            },
        )


class VariableImmutableFieldError(UnprocessableEntityError):
    """Raised when a PATCH attempts to modify an immutable field."""

    def __init__(self, field: str) -> None:
        error_code_map = {
            "scope": "PRICING_VARIABLE_SCOPE_IMMUTABLE",
            "code": "PRICING_VARIABLE_CODE_IMMUTABLE",
            "data_type": "PRICING_VARIABLE_DATA_TYPE_IMMUTABLE",
            "unit": "PRICING_VARIABLE_DATA_TYPE_IMMUTABLE",
            "is_fx_rate": "PRICING_VARIABLE_DATA_TYPE_IMMUTABLE",
        }
        super().__init__(
            message=f"Variable field {field!r} is immutable after creation.",
            error_code=error_code_map.get(field, "PRICING_VARIABLE_FIELD_IMMUTABLE"),
            details={"field": field},
        )


class VariableValidationError(ValidationError):
    """Raised when variable shape validation fails (code, unit, fx rules)."""

    def __init__(
        self,
        message: str,
        error_code: str = "PRICING_VARIABLE_INVALID",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


# ---------------------------------------------------------------------------
# Pricing context
# ---------------------------------------------------------------------------


class PricingContextNotFoundError(NotFoundError):
    """Raised when a pricing context does not exist (by id or code)."""

    def __init__(
        self,
        *,
        context_id: uuid.UUID | None = None,
        code: str | None = None,
    ) -> None:
        identifier = f"id={context_id}" if context_id is not None else f"code={code!r}"
        super().__init__(
            message=f"Pricing context not found ({identifier}).",
            error_code="PRICING_CONTEXT_NOT_FOUND",
            details={
                "context_id": str(context_id) if context_id else None,
                "code": code,
            },
        )


class PricingContextCodeTakenError(ConflictError):
    """Raised when creating a context with a code that already exists."""

    def __init__(self, code: str) -> None:
        super().__init__(
            message=f"Pricing context with code {code!r} already exists.",
            error_code="PRICING_CONTEXT_CODE_TAKEN",
            details={"code": code},
        )


class PricingContextVersionConflictError(ConflictError):
    """Raised on optimistic-lock mismatch during update/freeze/etc."""

    def __init__(
        self,
        context_id: uuid.UUID,
        expected_version: int,
        actual_version: int,
    ) -> None:
        super().__init__(
            message=(
                "Pricing context was modified by another request. "
                f"Expected version {expected_version}, got {actual_version}."
            ),
            error_code="PRICING_CONTEXT_VERSION_CONFLICT",
            details={
                "context_id": str(context_id),
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
        )


class PricingContextImmutableFieldError(UnprocessableEntityError):
    """Raised when a PATCH attempts to modify an immutable field (``code``)."""

    def __init__(self, field: str) -> None:
        super().__init__(
            message=f"Pricing context field {field!r} is immutable after creation.",
            error_code="PRICING_CONTEXT_FIELD_IMMUTABLE",
            details={"field": field},
        )


class PricingContextFrozenError(ConflictError):
    """Raised when an operation is not allowed while the context is frozen."""

    def __init__(self, context_id: uuid.UUID, operation: str) -> None:
        super().__init__(
            message=(
                f"Pricing context {context_id} is frozen; operation "
                f"{operation!r} is not allowed."
            ),
            error_code="PRICING_CONTEXT_FROZEN",
            details={"context_id": str(context_id), "operation": operation},
        )


class PricingContextValidationError(ValidationError):
    """Raised when context shape validation fails."""

    def __init__(
        self,
        message: str,
        error_code: str = "PRICING_CONTEXT_INVALID",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


# ---------------------------------------------------------------------------
# Formula version
# ---------------------------------------------------------------------------


class FormulaVersionNotFoundError(NotFoundError):
    """Raised when a ``FormulaVersion`` does not exist."""

    def __init__(
        self,
        *,
        version_id: uuid.UUID | None = None,
        context_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> None:
        if version_id is not None:
            msg = f"Formula version {version_id} not found."
        elif context_id is not None and status is not None:
            msg = f"No formula version with status={status!r} for context {context_id}."
        elif context_id is not None:
            msg = f"No formula version for context {context_id}."
        else:
            msg = "Formula version not found."
        super().__init__(
            message=msg,
            error_code="PRICING_FORMULA_VERSION_NOT_FOUND",
            details={
                "version_id": str(version_id) if version_id else None,
                "context_id": str(context_id) if context_id else None,
                "status": status,
            },
        )


class FormulaVersionConflictError(ConflictError):
    """Raised on optimistic-lock mismatch on a formula version."""

    def __init__(
        self,
        version_id: uuid.UUID,
        expected_version: int,
        actual_version: int,
    ) -> None:
        super().__init__(
            message=(
                "Formula version was modified by another request. "
                f"Expected version {expected_version}, got {actual_version}."
            ),
            error_code="PRICING_FORMULA_VERSION_CONFLICT",
            details={
                "version_id": str(version_id),
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
        )


class FormulaVersionImmutableError(ConflictError):
    """Raised on attempt to edit AST on a non-draft version (FRD §922)."""

    def __init__(self, version_id: uuid.UUID, status: str) -> None:
        super().__init__(
            message=(
                f"Formula version {version_id} is {status!r}; AST is immutable. "
                "Create a new draft instead."
            ),
            error_code="PRICING_FORMULA_VERSION_IMMUTABLE",
            details={"version_id": str(version_id), "status": status},
        )


class FormulaVersionInvalidStateError(ConflictError):
    """Raised on an illegal FSM transition (e.g. rollback a published version)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            error_code="PRICING_FORMULA_VERSION_INVALID_STATE",
            details=details,
        )


class FormulaValidationError(ValidationError):
    """Raised when AST shape / depth / length validation fails."""

    def __init__(
        self,
        message: str,
        error_code: str = "PRICING_FORMULA_AST_INVALID",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


# ---------------------------------------------------------------------------
# Category pricing settings
# ---------------------------------------------------------------------------


class CategoryPricingSettingsNotFoundError(NotFoundError):
    """Raised when no settings exist for the given (category_id, context_id)."""

    def __init__(self, *, category_id: uuid.UUID, context_id: uuid.UUID) -> None:
        super().__init__(
            message=(
                f"CategoryPricingSettings for category {category_id} and "
                f"context {context_id} not found."
            ),
            error_code="PRICING_CATEGORY_SETTINGS_NOT_FOUND",
            details={
                "category_id": str(category_id),
                "context_id": str(context_id),
            },
        )


class CategoryPricingSettingsConflictError(ConflictError):
    """Raised on optimistic-lock mismatch on settings update."""

    def __init__(
        self,
        *,
        category_id: uuid.UUID,
        context_id: uuid.UUID,
        expected_version: int,
        actual_version: int,
    ) -> None:
        super().__init__(
            message=(
                "Category pricing settings were modified by another request. "
                f"Expected version {expected_version}, got {actual_version}."
            ),
            error_code="PRICING_CATEGORY_SETTINGS_VERSION_CONFLICT",
            details={
                "category_id": str(category_id),
                "context_id": str(context_id),
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
        )


class CategoryPricingSettingsValidationError(ValidationError):
    """Raised on shape / range validation failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "PRICING_CATEGORY_SETTINGS_INVALID",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


# ---------------------------------------------------------------------------
# Supplier-type → context mapping
# ---------------------------------------------------------------------------


class SupplierTypeContextMappingNotFoundError(NotFoundError):
    """Raised when no mapping exists for the given supplier_type."""

    def __init__(self, supplier_type: str) -> None:
        super().__init__(
            message=f"Supplier-type context mapping for '{supplier_type}' not found.",
            error_code="PRICING_SUPPLIER_TYPE_MAPPING_NOT_FOUND",
            details={"supplier_type": supplier_type},
        )


class SupplierTypeContextMappingConflictError(ConflictError):
    """Raised on optimistic-lock mismatch when updating a mapping."""

    def __init__(
        self,
        supplier_type: str,
        expected_version: int,
        actual_version: int,
    ) -> None:
        super().__init__(
            message=(
                f"Supplier-type context mapping for '{supplier_type}' was modified "
                f"by another request. Expected version {expected_version}, "
                f"got {actual_version}."
            ),
            error_code="PRICING_SUPPLIER_TYPE_MAPPING_VERSION_CONFLICT",
            details={
                "supplier_type": supplier_type,
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
        )


class SupplierTypeContextMappingValidationError(ValidationError):
    """Raised on invalid supplier_type shape."""

    def __init__(
        self,
        message: str,
        error_code: str = "PRICING_SUPPLIER_TYPE_MAPPING_INVALID",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


# ---------------------------------------------------------------------------
# Formula evaluation (runtime)
# ---------------------------------------------------------------------------


class FormulaEvaluationError(UnprocessableEntityError):
    """Raised when a formula cannot be evaluated at runtime.

    Covers missing variables, division by zero, unknown operators/functions,
    arity mismatches, and non-decimal values. Translates to HTTP 422.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "PRICING_FORMULA_EVALUATION_FAILED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


# ---------------------------------------------------------------------------
# Supplier pricing settings
# ---------------------------------------------------------------------------


class SupplierPricingSettingsNotFoundError(NotFoundError):
    """Raised when no settings exist for the given supplier_id."""

    def __init__(self, *, supplier_id: uuid.UUID) -> None:
        super().__init__(
            message=f"SupplierPricingSettings for supplier {supplier_id} not found.",
            error_code="PRICING_SUPPLIER_SETTINGS_NOT_FOUND",
            details={"supplier_id": str(supplier_id)},
        )


class SupplierPricingSettingsConflictError(ConflictError):
    """Raised on optimistic-lock mismatch on settings update."""

    def __init__(
        self,
        *,
        supplier_id: uuid.UUID,
        expected_version: int,
        actual_version: int,
    ) -> None:
        super().__init__(
            message=(
                "Supplier pricing settings were modified by another request. "
                f"Expected version {expected_version}, got {actual_version}."
            ),
            error_code="PRICING_SUPPLIER_SETTINGS_VERSION_CONFLICT",
            details={
                "supplier_id": str(supplier_id),
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
        )


class SupplierPricingSettingsValidationError(ValidationError):
    """Raised on shape validation failures for supplier settings."""

    def __init__(
        self,
        message: str,
        error_code: str = "PRICING_SUPPLIER_SETTINGS_INVALID",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)
