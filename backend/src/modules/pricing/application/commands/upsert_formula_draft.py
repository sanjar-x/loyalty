"""Create or update the draft ``FormulaVersion`` for a context."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from src.modules.pricing.domain.exceptions import (
    FormulaVersionConflictError,
    PricingContextFrozenError,
    PricingContextNotFoundError,
)
from src.modules.pricing.domain.formula import FormulaVersion
from src.modules.pricing.domain.interfaces import (
    IFormulaVersionRepository,
    IPricingContextRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpsertFormulaDraftCommand:
    """Create a new draft (if none exists) or overwrite the current draft's AST."""

    context_id: uuid.UUID
    ast: dict[str, Any]
    actor_id: uuid.UUID
    expected_version_lock: int | None = None


@dataclass(frozen=True)
class UpsertFormulaDraftResult:
    version_id: uuid.UUID
    version_number: int
    version_lock: int
    created: bool


class UpsertFormulaDraftHandler:
    """Idempotent draft upsert — creates a new draft or updates the existing one."""

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
        self._logger = logger.bind(handler="UpsertFormulaDraftHandler")

    async def handle(
        self, command: UpsertFormulaDraftCommand
    ) -> UpsertFormulaDraftResult:
        async with self._uow:
            ctx = await self._context_repo.get_by_id(command.context_id)
            if ctx is None:
                raise PricingContextNotFoundError(context_id=command.context_id)
            if ctx.is_frozen:
                raise PricingContextFrozenError(
                    context_id=ctx.id, operation="upsert_formula_draft"
                )

            existing_draft = await self._formula_repo.get_draft_for_context(
                command.context_id
            )
            if existing_draft is not None:
                if (
                    command.expected_version_lock is not None
                    and existing_draft.version_lock != command.expected_version_lock
                ):
                    raise FormulaVersionConflictError(
                        version_id=existing_draft.id,
                        expected_version=command.expected_version_lock,
                        actual_version=existing_draft.version_lock,
                    )
                existing_draft.update_ast(
                    new_ast=command.ast, actor_id=command.actor_id
                )
                updated = await self._formula_repo.update(existing_draft)
                self._uow.register_aggregate(existing_draft)
                await self._uow.commit()
                self._logger.info(
                    "pricing_formula_draft_updated",
                    version_id=str(updated.id),
                    context_id=str(ctx.id),
                )
                return UpsertFormulaDraftResult(
                    version_id=updated.id,
                    version_number=updated.version_number,
                    version_lock=updated.version_lock,
                    created=False,
                )

            next_number = (
                await self._formula_repo.get_max_version_number(command.context_id) + 1
            )
            draft = FormulaVersion.create_draft(
                context_id=command.context_id,
                version_number=next_number,
                ast=command.ast,
                actor_id=command.actor_id,
            )
            added = await self._formula_repo.add(draft)
            self._uow.register_aggregate(draft)
            await self._uow.commit()
            self._logger.info(
                "pricing_formula_draft_created",
                version_id=str(added.id),
                context_id=str(ctx.id),
                version_number=added.version_number,
            )
            return UpsertFormulaDraftResult(
                version_id=added.id,
                version_number=added.version_number,
                version_lock=added.version_lock,
                created=True,
            )
