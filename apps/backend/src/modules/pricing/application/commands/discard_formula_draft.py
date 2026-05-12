"""Discard the current draft ``FormulaVersion`` for a context."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.pricing.domain.exceptions import (
    FormulaVersionNotFoundError,
    PricingContextFrozenError,
    PricingContextNotFoundError,
)
from src.modules.pricing.domain.interfaces import (
    IFormulaVersionRepository,
    IPricingContextRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DiscardFormulaDraftCommand:
    context_id: uuid.UUID
    actor_id: uuid.UUID


@dataclass(frozen=True)
class DiscardFormulaDraftResult:
    version_id: uuid.UUID


class DiscardFormulaDraftHandler:
    """Hard-delete the current draft and emit a discard event."""

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
        self._logger = logger.bind(handler="DiscardFormulaDraftHandler")

    async def handle(
        self, command: DiscardFormulaDraftCommand
    ) -> DiscardFormulaDraftResult:
        async with self._uow:
            ctx = await self._context_repo.get_by_id(command.context_id)
            if ctx is None:
                raise PricingContextNotFoundError(context_id=command.context_id)
            if ctx.is_frozen:
                raise PricingContextFrozenError(
                    context_id=ctx.id, operation="discard_formula_draft"
                )

            draft = await self._formula_repo.get_draft_for_context(command.context_id)
            if draft is None:
                raise FormulaVersionNotFoundError(
                    context_id=command.context_id, status="draft"
                )

            draft.discard(actor_id=command.actor_id)
            # Register aggregate BEFORE delete so the discard event is captured
            # for the outbox. The delete() is on the repository, not the aggregate.
            self._uow.register_aggregate(draft)
            await self._formula_repo.delete(draft.id)
            await self._uow.commit()
            self._logger.info(
                "pricing_formula_draft_discarded",
                version_id=str(draft.id),
                context_id=str(ctx.id),
            )
            return DiscardFormulaDraftResult(version_id=draft.id)
