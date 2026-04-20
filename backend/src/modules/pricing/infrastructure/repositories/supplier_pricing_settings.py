"""SQLAlchemy-backed repository for ``SupplierPricingSettings``."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.pricing.domain.exceptions import (
    SupplierPricingSettingsConflictError,
)
from src.modules.pricing.domain.interfaces import (
    ISupplierPricingSettingsRepository,
)
from src.modules.pricing.domain.supplier_pricing_settings import (
    SupplierPricingSettings,
)
from src.modules.pricing.infrastructure.models import SupplierPricingSettingsModel


def _values_to_json(values: dict[str, Decimal]) -> dict[str, str]:
    return {code: format(val, "f") for code, val in values.items()}


def _values_from_json(raw: dict[str, Any] | None) -> dict[str, Decimal]:
    if not raw:
        return {}
    return {code: Decimal(str(val)) for code, val in raw.items()}


class SupplierPricingSettingsRepository(ISupplierPricingSettingsRepository):
    """Data Mapper repository for ``SupplierPricingSettings``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(model: SupplierPricingSettingsModel) -> SupplierPricingSettings:
        settings = SupplierPricingSettings(
            id=model.id,
            supplier_id=model.supplier_id,
            values=_values_from_json(model.values),
            version_lock=model.version_lock,
            created_at=model.created_at,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
        )
        settings.clear_domain_events()
        return settings

    @staticmethod
    def _apply(
        model: SupplierPricingSettingsModel,
        settings: SupplierPricingSettings,
    ) -> None:
        model.values = _values_to_json(settings.values)
        model.version_lock = settings.version_lock
        model.updated_by = settings.updated_by

    async def add(
        self, settings: SupplierPricingSettings
    ) -> SupplierPricingSettings:
        model = SupplierPricingSettingsModel(
            id=settings.id,
            supplier_id=settings.supplier_id,
            values=_values_to_json(settings.values),
            version_lock=settings.version_lock,
            updated_by=settings.updated_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def update(
        self, settings: SupplierPricingSettings
    ) -> SupplierPricingSettings:
        model = await self._session.get(SupplierPricingSettingsModel, settings.id)
        if model is None:
            msg = f"SupplierPricingSettings {settings.id} disappeared before update"
            raise RuntimeError(msg)

        if model.version_lock != settings.version_lock - 1:
            raise SupplierPricingSettingsConflictError(
                supplier_id=settings.supplier_id,
                expected_version=settings.version_lock - 1,
                actual_version=model.version_lock,
            )

        self._apply(model, settings)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def delete(self, settings_id: uuid.UUID) -> None:
        model = await self._session.get(SupplierPricingSettingsModel, settings_id)
        if model is None:
            return
        await self._session.delete(model)
        await self._session.flush()

    async def get_by_supplier_id(
        self, supplier_id: uuid.UUID
    ) -> SupplierPricingSettings | None:
        stmt = select(SupplierPricingSettingsModel).where(
            SupplierPricingSettingsModel.supplier_id == supplier_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None
