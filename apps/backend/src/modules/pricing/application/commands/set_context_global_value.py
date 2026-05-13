"""Set (or update) a ``global``-scope variable value on a ``PricingContext``."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from src.modules.pricing.domain.exceptions import (
    PricingContextFrozenError,
    PricingContextNotFoundError,
    VariableNotFoundError,
    VariableValidationError,
)
from src.modules.pricing.domain.interfaces import (
    IPricingContextRepository,
    IVariableRepository,
)
from src.modules.pricing.domain.value_objects import VariableScope
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class SetContextGlobalValueCommand:
    context_id: uuid.UUID
    variable_code: str
    value: Decimal
    version_lock: int
    actor_id: uuid.UUID


@dataclass(frozen=True)
class SetContextGlobalValueResult:
    context_id: uuid.UUID
    variable_code: str
    value: Decimal
    version_lock: int


class SetContextGlobalValueHandler:
    def __init__(
        self,
        context_repo: IPricingContextRepository,
        variable_repo: IVariableRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._contexts = context_repo
        self._variables = variable_repo
        self._uow = uow
        self._logger = logger.bind(handler="SetContextGlobalValueHandler")

    async def handle(
        self, command: SetContextGlobalValueCommand
    ) -> SetContextGlobalValueResult:
        async with self._uow:
            ctx = await self._contexts.get_by_id(command.context_id)
            if ctx is None:
                raise PricingContextNotFoundError(context_id=command.context_id)

            if ctx.is_frozen:
                raise PricingContextFrozenError(
                    context_id=command.context_id, operation="set_global_value"
                )

            # Verify variable exists and is GLOBAL scope.
            variable = await self._variables.get_by_code(command.variable_code)
            if variable is None:
                raise VariableNotFoundError(code=command.variable_code)
            if variable.scope is not VariableScope.GLOBAL:
                raise VariableValidationError(
                    message=(
                        f"Variable {command.variable_code!r} has scope "
                        f"{variable.scope.value!r}; only global-scope variables "
                        "may be stored on a PricingContext."
                    ),
                    error_code="PRICING_VARIABLE_SCOPE_MISMATCH",
                    details={
                        "variable_code": command.variable_code,
                        "scope": variable.scope.value,
                    },
                )

            # Optimistic-lock guard: caller must pass current version_lock.
            if ctx.version_lock != command.version_lock:
                from src.modules.pricing.domain.exceptions import (
                    PricingContextVersionConflictError,
                )

                raise PricingContextVersionConflictError(
                    context_id=ctx.id,
                    expected_version=command.version_lock,
                    actual_version=ctx.version_lock,
                )

            ctx.set_global_value(
                variable_code=command.variable_code,
                value=command.value,
                actor_id=command.actor_id,
            )
            updated = await self._contexts.update(ctx)
            self._uow.register_aggregate(ctx)
            await self._uow.commit()

            self._logger.info(
                "pricing_context_global_value_set",
                context_id=str(updated.id),
                variable_code=command.variable_code,
                value=str(command.value),
            )
            return SetContextGlobalValueResult(
                context_id=updated.id,
                variable_code=command.variable_code,
                value=command.value,
                version_lock=updated.version_lock,
            )
