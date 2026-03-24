"""Supplier repository port interfaces."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.value_objects import SupplierType


class ISupplierRepository(ABC):
    """Write-side repository for the Supplier aggregate."""

    @abstractmethod
    async def add(self, entity: Supplier) -> Supplier: ...

    @abstractmethod
    async def get(self, entity_id: uuid.UUID) -> Supplier | None: ...

    @abstractmethod
    async def update(self, entity: Supplier) -> Supplier: ...


@dataclass(frozen=True)
class SupplierInfo:
    """Lightweight DTO returned by the cross-module query service."""

    id: uuid.UUID
    name: str
    type: SupplierType
    is_active: bool


class ISupplierQueryService(ABC):
    """Read-only interface for cross-module supplier lookups.

    The catalog module depends on this interface to validate supplier
    references without importing supplier internals.
    """

    @abstractmethod
    async def get_supplier_info(self, supplier_id: uuid.UUID) -> SupplierInfo | None: ...

    @abstractmethod
    async def assert_supplier_active(self, supplier_id: uuid.UUID) -> SupplierInfo: ...
