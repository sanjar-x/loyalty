"""SQLAlchemy-backed repository for ``SupplierTypeContextMapping``."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.pricing.domain.entities.supplier_type_context_mapping import (
    SupplierTypeContextMapping,
)
from src.modules.pricing.domain.exceptions import (
    SupplierTypeContextMappingConflictError,
)
from src.modules.pricing.domain.interfaces import (
    ISupplierTypeContextMappingRepository,
)
from src.modules.pricing.infrastructure.models import (
    SupplierTypeContextMappingModel,
)


class SupplierTypeContextMappingRepository(ISupplierTypeContextMappingRepository):
    """Data Mapper repository for ``SupplierTypeContextMapping``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(
        model: SupplierTypeContextMappingModel,
    ) -> SupplierTypeContextMapping:
        mapping = SupplierTypeContextMapping(
            id=model.id,
            supplier_type=model.supplier_type,
            context_id=model.context_id,
            version_lock=model.version_lock,
            created_at=model.created_at,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
        )
        mapping.clear_domain_events()
        return mapping

    @staticmethod
    def _apply(
        model: SupplierTypeContextMappingModel,
        mapping: SupplierTypeContextMapping,
    ) -> None:
        model.context_id = mapping.context_id
        model.version_lock = mapping.version_lock
        model.updated_by = mapping.updated_by

    # ------------------------------------------------------------------
    # Interface methods
    # ------------------------------------------------------------------

    async def add(
        self, mapping: SupplierTypeContextMapping
    ) -> SupplierTypeContextMapping:
        model = SupplierTypeContextMappingModel(
            id=mapping.id,
            supplier_type=mapping.supplier_type,
            context_id=mapping.context_id,
            version_lock=mapping.version_lock,
            updated_by=mapping.updated_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def update(
        self, mapping: SupplierTypeContextMapping
    ) -> SupplierTypeContextMapping:
        model = await self._session.get(SupplierTypeContextMappingModel, mapping.id)
        if model is None:
            msg = (
                f"SupplierTypeContextMapping {mapping.id} disappeared before update"
            )
            raise RuntimeError(msg)

        if model.version_lock != mapping.version_lock - 1:
            raise SupplierTypeContextMappingConflictError(
                supplier_type=mapping.supplier_type,
                expected_version=mapping.version_lock - 1,
                actual_version=model.version_lock,
            )

        self._apply(model, mapping)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def delete(self, mapping_id: uuid.UUID) -> None:
        model = await self._session.get(
            SupplierTypeContextMappingModel, mapping_id
        )
        if model is None:
            return
        await self._session.delete(model)
        await self._session.flush()

    async def get_by_supplier_type(
        self, supplier_type: str
    ) -> SupplierTypeContextMapping | None:
        stmt = select(SupplierTypeContextMappingModel).where(
            SupplierTypeContextMappingModel.supplier_type == supplier_type
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_all(self) -> list[SupplierTypeContextMapping]:
        stmt = select(SupplierTypeContextMappingModel).order_by(
            SupplierTypeContextMappingModel.supplier_type.asc()
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]
