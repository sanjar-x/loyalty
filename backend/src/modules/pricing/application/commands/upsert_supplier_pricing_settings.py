"""Upsert per-supplier pricing settings (PUT semantics, full replace)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.modules.pricing.domain.entities.supplier_pricing_settings import (
    SupplierPricingSettings,
)
from src.modules.pricing.domain.interfaces import (
    ISupplierPricingSettingsRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpsertSupplierPricingSettingsCommand:
    supplier_id: uuid.UUID
    values: dict[str, Decimal]
    actor_id: uuid.UUID
    expected_version_lock: int | None = None


@dataclass(frozen=True)
class UpsertSupplierPricingSettingsResult:
    settings_id: uuid.UUID
    supplier_id: uuid.UUID
    version_lock: int
    created: bool


class UpsertSupplierPricingSettingsHandler:
    """Create or fully replace (PUT) settings for a supplier."""

    def __init__(
        self,
        settings_repo: ISupplierPricingSettingsRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._settings_repo = settings_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpsertSupplierPricingSettingsHandler")

    async def handle(
        self, command: UpsertSupplierPricingSettingsCommand
    ) -> UpsertSupplierPricingSettingsResult:
        async with self._uow:
            existing = await self._settings_repo.get_by_supplier_id(
                command.supplier_id
            )

            if existing is not None:
                existing.replace(
                    values=command.values,
                    actor_id=command.actor_id,
                )
                updated = await self._settings_repo.update(existing)
                self._uow.register_aggregate(existing)
                await self._uow.commit()
                self._logger.info(
                    "pricing_supplier_settings_updated",
                    settings_id=str(updated.id),
                    supplier_id=str(updated.supplier_id),
                )
                return UpsertSupplierPricingSettingsResult(
                    settings_id=updated.id,
                    supplier_id=updated.supplier_id,
                    version_lock=updated.version_lock,
                    created=False,
                )

            settings = SupplierPricingSettings.create(
                supplier_id=command.supplier_id,
                values=command.values,
                actor_id=command.actor_id,
            )
            added = await self._settings_repo.add(settings)
            self._uow.register_aggregate(settings)
            await self._uow.commit()
            self._logger.info(
                "pricing_supplier_settings_created",
                settings_id=str(added.id),
                supplier_id=str(added.supplier_id),
            )
            return UpsertSupplierPricingSettingsResult(
                settings_id=added.id,
                supplier_id=added.supplier_id,
                version_lock=added.version_lock,
                created=True,
            )


__all__: list[Any] = [
    "UpsertSupplierPricingSettingsCommand",
    "UpsertSupplierPricingSettingsHandler",
    "UpsertSupplierPricingSettingsResult",
]
