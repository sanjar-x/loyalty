"""Upsert per-(category, context) pricing settings (PUT semantics)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.modules.pricing.domain.category_pricing_settings import (
    CategoryPricingSettings,
    RangeBucket,
)
from src.modules.pricing.domain.exceptions import (
    PricingContextFrozenError,
    PricingContextNotFoundError,
)
from src.modules.pricing.domain.interfaces import (
    ICategoryPricingSettingsRepository,
    IPricingContextRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpsertCategoryPricingSettingsCommand:
    category_id: uuid.UUID
    context_id: uuid.UUID
    values: dict[str, Decimal]
    ranges: list[RangeBucket]
    explicit_no_ranges: bool
    actor_id: uuid.UUID
    expected_version_lock: int | None = None


@dataclass(frozen=True)
class UpsertCategoryPricingSettingsResult:
    settings_id: uuid.UUID
    category_id: uuid.UUID
    context_id: uuid.UUID
    version_lock: int
    created: bool


class UpsertCategoryPricingSettingsHandler:
    """Create or fully replace (PUT) settings for (category, context)."""

    def __init__(
        self,
        settings_repo: ICategoryPricingSettingsRepository,
        context_repo: IPricingContextRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._settings_repo = settings_repo
        self._context_repo = context_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpsertCategoryPricingSettingsHandler")

    async def handle(
        self, command: UpsertCategoryPricingSettingsCommand
    ) -> UpsertCategoryPricingSettingsResult:
        async with self._uow:
            ctx = await self._context_repo.get_by_id(command.context_id)
            if ctx is None:
                raise PricingContextNotFoundError(context_id=command.context_id)
            if ctx.is_frozen:
                raise PricingContextFrozenError(
                    context_id=ctx.id,
                    operation="upsert_category_pricing_settings",
                )

            existing = await self._settings_repo.get_by_category_and_context(
                category_id=command.category_id,
                context_id=command.context_id,
            )

            if existing is not None:
                existing.replace(
                    values=command.values,
                    ranges=command.ranges,
                    explicit_no_ranges=command.explicit_no_ranges,
                    actor_id=command.actor_id,
                )
                updated = await self._settings_repo.update(existing)
                self._uow.register_aggregate(existing)
                await self._uow.commit()
                self._logger.info(
                    "pricing_category_settings_updated",
                    settings_id=str(updated.id),
                    category_id=str(updated.category_id),
                    context_id=str(updated.context_id),
                )
                return UpsertCategoryPricingSettingsResult(
                    settings_id=updated.id,
                    category_id=updated.category_id,
                    context_id=updated.context_id,
                    version_lock=updated.version_lock,
                    created=False,
                )

            settings = CategoryPricingSettings.create(
                category_id=command.category_id,
                context_id=command.context_id,
                values=command.values,
                ranges=command.ranges,
                explicit_no_ranges=command.explicit_no_ranges,
                actor_id=command.actor_id,
            )
            added = await self._settings_repo.add(settings)
            self._uow.register_aggregate(settings)
            await self._uow.commit()
            self._logger.info(
                "pricing_category_settings_created",
                settings_id=str(added.id),
                category_id=str(added.category_id),
                context_id=str(added.context_id),
            )
            return UpsertCategoryPricingSettingsResult(
                settings_id=added.id,
                category_id=added.category_id,
                context_id=added.context_id,
                version_lock=added.version_lock,
                created=True,
            )


__all__: list[Any] = [
    "UpsertCategoryPricingSettingsCommand",
    "UpsertCategoryPricingSettingsHandler",
    "UpsertCategoryPricingSettingsResult",
]
