"""Rollback to a previously-archived ``FormulaVersion``.

The target (archived) version is restored to ``published`` status, and the
current published version (if any and different from the target) is archived.
``PricingContext.active_formula_version_id`` is updated accordingly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.pricing.domain.exceptions import (
    FormulaVersionInvalidStateError,
    FormulaVersionNotFoundError,
    PricingContextFrozenError,
    PricingContextNotFoundError,
)
from src.modules.pricing.domain.interfaces import (
    IFormulaVersionRepository,
    IPricingContextRepository,
)
from src.modules.pricing.domain.value_objects import FormulaStatus
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RollbackFormulaCommand:
    context_id: uuid.UUID
    target_version_id: uuid.UUID
    actor_id: uuid.UUID


@dataclass(frozen=True)
class RollbackFormulaResult:
    version_id: uuid.UUID
    rolled_back_from_version_id: uuid.UUID | None


class RollbackFormulaHandler:
    def __init__(
        self,
        formula_repo: IFormulaVersionRepository,
        context_repo: IPricingContextRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._formula_repo = formula_repo
        self._context_repo = context_repo
        self._uow = uow
        self._logger = logger.bind(handler="RollbackFormulaHandler")

    async def handle(self, command: RollbackFormulaCommand) -> RollbackFormulaResult:
        async with self._uow:
            ctx = await self._context_repo.get_by_id(command.context_id)
            if ctx is None:
                raise PricingContextNotFoundError(context_id=command.context_id)
            if ctx.is_frozen:
                raise PricingContextFrozenError(
                    context_id=ctx.id, operation="rollback_formula"
                )

            target = await self._formula_repo.get_by_id(command.target_version_id)
            if target is None or target.context_id != command.context_id:
                raise FormulaVersionNotFoundError(version_id=command.target_version_id)
            if target.status is not FormulaStatus.ARCHIVED:
                raise FormulaVersionInvalidStateError(
                    message=(
                        "Only archived versions can be rolled back to "
                        f"(current status: {target.status.value})."
                    ),
                    details={
                        "version_id": str(target.id),
                        "status": target.status.value,
                    },
                )

            current_published = await self._formula_repo.get_published_for_context(
                command.context_id
            )
            rolled_back_from: uuid.UUID | None = None
            if current_published is not None and current_published.id != target.id:
                rolled_back_from = current_published.id
                current_published.archive(actor_id=command.actor_id)
                await self._formula_repo.update(current_published)
                await self._uow.flush()
                self._uow.register_aggregate(current_published)

            target.restore_as_published(
                actor_id=command.actor_id,
                rolled_back_from_version_id=rolled_back_from,
            )
            await self._formula_repo.update(target)
            self._uow.register_aggregate(target)

            ctx.set_active_formula_version(
                version_id=target.id, actor_id=command.actor_id
            )
            await self._context_repo.update(ctx)
            self._uow.register_aggregate(ctx)

            await self._uow.commit()

            self._logger.info(
                "pricing_formula_rolled_back",
                version_id=str(target.id),
                context_id=str(ctx.id),
                rolled_back_from_version_id=(
                    str(rolled_back_from) if rolled_back_from else None
                ),
            )
            return RollbackFormulaResult(
                version_id=target.id,
                rolled_back_from_version_id=rolled_back_from,
            )
