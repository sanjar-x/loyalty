"""Delete per-(category, context) pricing settings."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.pricing.domain.exceptions import (
    CategoryPricingSettingsNotFoundError,
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
class DeleteCategoryPricingSettingsCommand:
    category_id: uuid.UUID
    context_id: uuid.UUID
    actor_id: uuid.UUID


class DeleteCategoryPricingSettingsHandler:
    """Hard-delete settings for (category, context); 404 if missing, 423 if frozen."""

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
        self._logger = logger.bind(handler="DeleteCategoryPricingSettingsHandler")

    async def handle(self, command: DeleteCategoryPricingSettingsCommand) -> None:
        async with self._uow:
            ctx = await self._context_repo.get_by_id(command.context_id)
            if ctx is None:
                raise PricingContextNotFoundError(context_id=command.context_id)
            if ctx.is_frozen:
                raise PricingContextFrozenError(
                    context_id=ctx.id,
                    operation="delete_category_pricing_settings",
                )

            existing = await self._settings_repo.get_by_category_and_context(
                category_id=command.category_id,
                context_id=command.context_id,
            )
            if existing is None:
                raise CategoryPricingSettingsNotFoundError(
                    category_id=command.category_id,
                    context_id=command.context_id,
                )

            existing.mark_deleted(actor_id=command.actor_id)
            self._uow.register_aggregate(existing)
            await self._settings_repo.delete(existing.id)
            await self._uow.commit()
            self._logger.info(
                "pricing_category_settings_deleted",
                settings_id=str(existing.id),
                category_id=str(existing.category_id),
                context_id=str(existing.context_id),
            )
