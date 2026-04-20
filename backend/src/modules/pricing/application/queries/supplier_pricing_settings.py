"""Query: get per-supplier pricing settings."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.pricing.domain.exceptions import (
    SupplierPricingSettingsNotFoundError,
)
from src.modules.pricing.domain.interfaces import (
    ISupplierPricingSettingsRepository,
)
from src.modules.pricing.domain.supplier_pricing_settings import (
    SupplierPricingSettings,
)


@dataclass(frozen=True)
class GetSupplierPricingSettingsQuery:
    supplier_id: uuid.UUID


class GetSupplierPricingSettingsHandler:
    """Direct lookup — returns the settings or raises ``NotFoundError``."""

    def __init__(self, settings_repo: ISupplierPricingSettingsRepository) -> None:
        self._settings_repo = settings_repo

    async def handle(
        self, query: GetSupplierPricingSettingsQuery
    ) -> SupplierPricingSettings:
        settings = await self._settings_repo.get_by_supplier_id(query.supplier_id)
        if settings is None:
            raise SupplierPricingSettingsNotFoundError(
                supplier_id=query.supplier_id
            )
        return settings
