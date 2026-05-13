"""Queries for ``SupplierType → PricingContext`` mappings."""

from __future__ import annotations

from dataclasses import dataclass

from src.modules.pricing.domain.entities.supplier_type_context_mapping import (
    SupplierTypeContextMapping,
)
from src.modules.pricing.domain.exceptions import (
    SupplierTypeContextMappingNotFoundError,
)
from src.modules.pricing.domain.interfaces import (
    ISupplierTypeContextMappingRepository,
)


@dataclass(frozen=True)
class GetSupplierTypeContextMappingQuery:
    supplier_type: str


class GetSupplierTypeContextMappingHandler:
    """Fetch a single mapping by ``supplier_type``; 404 if absent."""

    def __init__(self, mapping_repo: ISupplierTypeContextMappingRepository) -> None:
        self._mapping_repo = mapping_repo

    async def handle(
        self, query: GetSupplierTypeContextMappingQuery
    ) -> SupplierTypeContextMapping:
        mapping = await self._mapping_repo.get_by_supplier_type(query.supplier_type)
        if mapping is None:
            raise SupplierTypeContextMappingNotFoundError(
                supplier_type=query.supplier_type
            )
        return mapping


@dataclass(frozen=True)
class ListSupplierTypeContextMappingsQuery:
    """Marker query; currently returns all mappings unfiltered."""


class ListSupplierTypeContextMappingsHandler:
    def __init__(self, mapping_repo: ISupplierTypeContextMappingRepository) -> None:
        self._mapping_repo = mapping_repo

    async def handle(
        self, query: ListSupplierTypeContextMappingsQuery
    ) -> list[SupplierTypeContextMapping]:
        return await self._mapping_repo.list_all()
