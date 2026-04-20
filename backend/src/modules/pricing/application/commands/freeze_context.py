"""Freeze a ``PricingContext`` (emergency kill-switch for recalc)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.pricing.domain.exceptions import PricingContextNotFoundError
from src.modules.pricing.domain.interfaces import IPricingContextRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class FreezeContextCommand:
    context_id: uuid.UUID
    reason: str
    actor_id: uuid.UUID


@dataclass(frozen=True)
class FreezeContextResult:
    context_id: uuid.UUID
    version_lock: int


class FreezeContextHandler:
    def __init__(
        self,
        repo: IPricingContextRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="FreezeContextHandler")

    async def handle(self, command: FreezeContextCommand) -> FreezeContextResult:
        async with self._uow:
            ctx = await self._repo.get_by_id(command.context_id)
            if ctx is None:
                raise PricingContextNotFoundError(context_id=command.context_id)

            ctx.freeze(reason=command.reason, actor_id=command.actor_id)
            updated = await self._repo.update(ctx)
            self._uow.register_aggregate(ctx)
            await self._uow.commit()

            self._logger.info(
                "pricing_context_frozen",
                context_id=str(updated.id),
                code=updated.code,
                reason=command.reason,
            )
            return FreezeContextResult(
                context_id=updated.id, version_lock=updated.version_lock
            )
