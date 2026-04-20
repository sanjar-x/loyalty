"""Soft-delete a ``ProductPricingProfile``."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.pricing.domain.exceptions import (
    ProductPricingProfileNotFoundError,
)
from src.modules.pricing.domain.interfaces import IProductPricingProfileRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteProductPricingProfileCommand:
    product_id: uuid.UUID
    actor_id: uuid.UUID | None = None


@dataclass(frozen=True)
class DeleteProductPricingProfileResult:
    profile_id: uuid.UUID


class DeleteProductPricingProfileHandler:
    """Soft-delete a profile by ``product_id``; history is preserved."""

    def __init__(
        self,
        repo: IProductPricingProfileRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteProductPricingProfileHandler")

    async def handle(
        self, command: DeleteProductPricingProfileCommand
    ) -> DeleteProductPricingProfileResult:
        async with self._uow:
            profile = await self._repo.get_by_product_id_for_update(command.product_id)
            if profile is None:
                raise ProductPricingProfileNotFoundError(command.product_id)

            profile.soft_delete(actor_id=command.actor_id)
            updated = await self._repo.update(profile)
            self._uow.register_aggregate(profile)
            await self._uow.commit()
            self._logger.info(
                "pricing_profile_deleted",
                product_id=str(updated.product_id),
                profile_id=str(updated.id),
            )
            return DeleteProductPricingProfileResult(profile_id=updated.id)
