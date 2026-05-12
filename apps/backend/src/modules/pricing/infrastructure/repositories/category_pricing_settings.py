"""SQLAlchemy-backed repository for ``CategoryPricingSettings``."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.pricing.domain.entities.category_pricing_settings import (
    CategoryPricingSettings,
    RangeBucket,
)
from src.modules.pricing.domain.exceptions import (
    CategoryPricingSettingsConflictError,
)
from src.modules.pricing.domain.interfaces import (
    ICategoryPricingSettingsRepository,
)
from src.modules.pricing.infrastructure.models import CategoryPricingSettingsModel


def _values_to_json(values: dict[str, Decimal]) -> dict[str, str]:
    return {code: format(val, "f") for code, val in values.items()}


def _values_from_json(raw: dict[str, Any] | None) -> dict[str, Decimal]:
    if not raw:
        return {}
    return {code: Decimal(str(val)) for code, val in raw.items()}


def _range_to_json(bucket: RangeBucket) -> dict[str, Any]:
    return {
        "id": str(bucket.id),
        "min": format(bucket.min, "f"),
        "max": None if bucket.max is None else format(bucket.max, "f"),
        "values": _values_to_json(bucket.values),
    }


def _range_from_json(raw: dict[str, Any]) -> RangeBucket:
    return RangeBucket(
        id=uuid.UUID(raw["id"]),
        min=Decimal(str(raw["min"])),
        max=None if raw.get("max") is None else Decimal(str(raw["max"])),
        values=_values_from_json(raw.get("values")),
    )


class CategoryPricingSettingsRepository(ICategoryPricingSettingsRepository):
    """Data Mapper repository for ``CategoryPricingSettings``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(model: CategoryPricingSettingsModel) -> CategoryPricingSettings:
        settings = CategoryPricingSettings(
            id=model.id,
            category_id=model.category_id,
            context_id=model.context_id,
            values=_values_from_json(model.values),
            ranges=[_range_from_json(r) for r in (model.ranges or [])],
            explicit_no_ranges=model.explicit_no_ranges,
            version_lock=model.version_lock,
            created_at=model.created_at,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
        )
        settings.clear_domain_events()
        return settings

    @staticmethod
    def _apply(
        model: CategoryPricingSettingsModel,
        settings: CategoryPricingSettings,
    ) -> None:
        model.values = _values_to_json(settings.values)
        model.ranges = [_range_to_json(r) for r in settings.ranges]
        model.explicit_no_ranges = settings.explicit_no_ranges
        model.version_lock = settings.version_lock
        model.updated_by = settings.updated_by

    # ------------------------------------------------------------------
    # Interface methods
    # ------------------------------------------------------------------

    async def add(self, settings: CategoryPricingSettings) -> CategoryPricingSettings:
        model = CategoryPricingSettingsModel(
            id=settings.id,
            category_id=settings.category_id,
            context_id=settings.context_id,
            values=_values_to_json(settings.values),
            ranges=[_range_to_json(r) for r in settings.ranges],
            explicit_no_ranges=settings.explicit_no_ranges,
            version_lock=settings.version_lock,
            updated_by=settings.updated_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def update(
        self, settings: CategoryPricingSettings
    ) -> CategoryPricingSettings:
        model = await self._session.get(CategoryPricingSettingsModel, settings.id)
        if model is None:
            msg = f"CategoryPricingSettings {settings.id} disappeared before update"
            raise RuntimeError(msg)

        if model.version_lock != settings.version_lock - 1:
            raise CategoryPricingSettingsConflictError(
                category_id=settings.category_id,
                context_id=settings.context_id,
                expected_version=settings.version_lock - 1,
                actual_version=model.version_lock,
            )

        self._apply(model, settings)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def delete(self, settings_id: uuid.UUID) -> None:
        model = await self._session.get(CategoryPricingSettingsModel, settings_id)
        if model is None:
            return
        await self._session.delete(model)
        await self._session.flush()

    async def get_by_category_and_context(
        self,
        *,
        category_id: uuid.UUID,
        context_id: uuid.UUID,
    ) -> CategoryPricingSettings | None:
        stmt = select(CategoryPricingSettingsModel).where(
            CategoryPricingSettingsModel.category_id == category_id,
            CategoryPricingSettingsModel.context_id == context_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None
