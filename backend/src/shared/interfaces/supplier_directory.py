"""
Supplier directory port (Context-Map Published Language).

Defines a minimal cross-module contract for consumers (e.g. catalog, pricing)
that need to verify a supplier reference without coupling to the supplier
bounded context's internal domain.

The supplier module provides the implementation under
``src.modules.supplier.infrastructure``; consumers depend only on this port
and the ``SupplierSnapshot`` DTO defined here.

``type_code`` is a plain string (``"local"`` / ``"cross_border"``) rather
than a shared enum to keep the contract resilient to supplier-internal
enum evolution; consumers compare against string literals defined in their
own bounded context.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from src.shared.exceptions import NotFoundError, UnprocessableEntityError


@dataclass(frozen=True)
class SupplierSnapshot:
    """Read-only projection of a supplier suitable for cross-module use."""

    id: uuid.UUID
    name: str
    type_code: str
    is_active: bool


class SupplierDirectoryNotFoundError(NotFoundError):
    """Raised when the directory has no record for the given supplier id."""

    def __init__(self, supplier_id: uuid.UUID | str) -> None:
        super().__init__(
            message=f"Supplier with ID {supplier_id} not found.",
            error_code="SUPPLIER_NOT_FOUND",
            details={"supplier_id": str(supplier_id)},
        )


class SupplierDirectoryInactiveError(UnprocessableEntityError):
    """Raised when the directory lookup succeeds but the supplier is inactive."""

    def __init__(self, supplier_id: uuid.UUID | str) -> None:
        super().__init__(
            message=(
                f"Supplier {supplier_id} is inactive and cannot be assigned "
                "to new products."
            ),
            error_code="SUPPLIER_INACTIVE",
            details={"supplier_id": str(supplier_id)},
        )


@runtime_checkable
class ISupplierDirectory(Protocol):
    """Port for resolving supplier references across module boundaries."""

    async def get_snapshot(self, supplier_id: uuid.UUID) -> SupplierSnapshot | None: ...

    async def assert_active(self, supplier_id: uuid.UUID) -> SupplierSnapshot:
        """Return the snapshot or raise if missing / inactive.

        Raises:
            SupplierDirectoryNotFoundError: supplier id unknown.
            SupplierDirectoryInactiveError: supplier exists but is inactive.
        """
        ...
