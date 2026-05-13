"""Query: get per-(category, context) pricing settings (direct — no inheritance)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.pricing.domain.entities.category_pricing_settings import (
    CategoryPricingSettings,
)
from src.modules.pricing.domain.exceptions import (
    CategoryPricingSettingsNotFoundError,
)
from src.modules.pricing.domain.interfaces import (
    ICategoryPricingSettingsRepository,
)


@dataclass(frozen=True)
class GetCategoryPricingSettingsQuery:
    category_id: uuid.UUID
    context_id: uuid.UUID


class GetCategoryPricingSettingsHandler:
    """Direct lookup — returns the settings or raises ``NotFoundError``."""

    def __init__(self, settings_repo: ICategoryPricingSettingsRepository) -> None:
        self._settings_repo = settings_repo

    async def handle(
        self, query: GetCategoryPricingSettingsQuery
    ) -> CategoryPricingSettings:
        settings = await self._settings_repo.get_by_category_and_context(
            category_id=query.category_id,
            context_id=query.context_id,
        )
        if settings is None:
            raise CategoryPricingSettingsNotFoundError(
                category_id=query.category_id,
                context_id=query.context_id,
            )
        return settings
