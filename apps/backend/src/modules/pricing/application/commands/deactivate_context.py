"""Soft-deactivate a ``PricingContext`` (sets ``is_active=false``)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.pricing.domain.exceptions import PricingContextNotFoundError
from src.modules.pricing.domain.interfaces import IPricingContextRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeactivateContextCommand:
    context_id: uuid.UUID
    actor_id: uuid.UUID


@dataclass(frozen=True)
class DeactivateContextResult:
    context_id: uuid.UUID
    version_lock: int


class DeactivateContextHandler:
    def __init__(
        self,
        repo: IPricingContextRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="DeactivateContextHandler")

    async def handle(
        self, command: DeactivateContextCommand
    ) -> DeactivateContextResult:
        async with self._uow:
            ctx = await self._repo.get_by_id(command.context_id)
            if ctx is None:
                raise PricingContextNotFoundError(context_id=command.context_id)

            if not ctx.is_active:
                # Idempotent: already inactive.
                return DeactivateContextResult(
                    context_id=ctx.id, version_lock=ctx.version_lock
                )

            ctx.deactivate(actor_id=command.actor_id)
            updated = await self._repo.update(ctx)
            self._uow.register_aggregate(ctx)
            await self._uow.commit()

            self._logger.info(
                "pricing_context_deactivated",
                context_id=str(updated.id),
                code=updated.code,
            )
            return DeactivateContextResult(
                context_id=updated.id, version_lock=updated.version_lock
            )
