"""Supplier domain exceptions."""

import uuid

from src.shared.exceptions import ConflictError, NotFoundError, UnprocessableEntityError


class SupplierNotFoundError(NotFoundError):
    def __init__(self, supplier_id: uuid.UUID | str):
        super().__init__(
            message=f"Supplier with ID {supplier_id} not found.",
            error_code="SUPPLIER_NOT_FOUND",
            details={"supplier_id": str(supplier_id)},
        )


class SupplierInactiveError(UnprocessableEntityError):
    def __init__(self, supplier_id: uuid.UUID | str):
        super().__init__(
            message=f"Supplier {supplier_id} is inactive and cannot be assigned to new products.",
            error_code="SUPPLIER_INACTIVE",
            details={"supplier_id": str(supplier_id)},
        )


class SupplierAlreadyActiveError(ConflictError):
    def __init__(self, supplier_id: uuid.UUID | str):
        super().__init__(
            message=f"Supplier {supplier_id} is already active.",
            error_code="SUPPLIER_ALREADY_ACTIVE",
            details={"supplier_id": str(supplier_id)},
        )


class SupplierAlreadyInactiveError(ConflictError):
    def __init__(self, supplier_id: uuid.UUID | str):
        super().__init__(
            message=f"Supplier {supplier_id} is already inactive.",
            error_code="SUPPLIER_ALREADY_INACTIVE",
            details={"supplier_id": str(supplier_id)},
        )


class SourceUrlRequiredError(UnprocessableEntityError):
    def __init__(self):
        super().__init__(
            message="source_url is required for cross-border suppliers.",
            error_code="SOURCE_URL_REQUIRED",
        )
