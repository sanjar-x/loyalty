"""Publish the current draft ``FormulaVersion`` atomically.

This is a multi-aggregate transition:

1. The current draft transitions ``draft → published``.
2. Any existing published version for the same context transitions
   ``published → archived``.
3. The ``PricingContext.active_formula_version_id`` is updated to point at
   the newly-published version.

All three updates happen inside a single UoW (therefore a single DB
transaction), so the "at most one published per context" invariant (enforced
by the partial unique index) is preserved even under concurrency.
"""

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
class PublishFormulaDraftCommand:
    context_id: uuid.UUID
    actor_id: uuid.UUID


@dataclass(frozen=True)
class PublishFormulaDraftResult:
    version_id: uuid.UUID
    version_number: int
    previous_version_id: uuid.UUID | None


class PublishFormulaDraftHandler:
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
        self._logger = logger.bind(handler="PublishFormulaDraftHandler")

    async def handle(
        self, command: PublishFormulaDraftCommand
    ) -> PublishFormulaDraftResult:
        async with self._uow:
            ctx = await self._context_repo.get_by_id(command.context_id)
            if ctx is None:
                raise PricingContextNotFoundError(context_id=command.context_id)
            if ctx.is_frozen:
                raise PricingContextFrozenError(
                    context_id=ctx.id, operation="publish_formula_draft"
                )

            draft = await self._formula_repo.get_draft_for_context(command.context_id)
            if draft is None:
                raise FormulaVersionNotFoundError(
                    context_id=command.context_id, status="draft"
                )

            old_published = await self._formula_repo.get_published_for_context(
                command.context_id
            )

            # 1. Archive the current published version (if any).
            # Archive it FIRST and flush — otherwise the partial unique index
            # on (context_id) WHERE status='published' would block the draft's
            # transition to published within the same transaction.
            previous_version_id: uuid.UUID | None = None
            if old_published is not None:
                previous_version_id = old_published.id
                old_published.archive(actor_id=command.actor_id)
                await self._formula_repo.update(old_published)
                await self._uow.flush()
                self._uow.register_aggregate(old_published)

            # 2. Publish the draft.
            draft.publish(
                actor_id=command.actor_id, previous_version_id=previous_version_id
            )
            await self._formula_repo.update(draft)
            self._uow.register_aggregate(draft)

            # 3. Update the context pointer.
            ctx.set_active_formula_version(
                version_id=draft.id, actor_id=command.actor_id
            )
            await self._context_repo.update(ctx)
            self._uow.register_aggregate(ctx)

            await self._uow.commit()

            self._logger.info(
                "pricing_formula_published",
                version_id=str(draft.id),
                context_id=str(ctx.id),
                version_number=draft.version_number,
                previous_version_id=(
                    str(previous_version_id) if previous_version_id else None
                ),
            )
            return PublishFormulaDraftResult(
                version_id=draft.id,
                version_number=draft.version_number,
                previous_version_id=previous_version_id,
            )
