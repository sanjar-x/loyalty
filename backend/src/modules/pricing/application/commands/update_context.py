"""Update mutable fields of a ``PricingContext``."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from src.modules.pricing.domain.exceptions import (
    PricingContextImmutableFieldError,
    PricingContextNotFoundError,
    PricingContextValidationError,
    PricingContextVersionConflictError,
)
from src.modules.pricing.domain.interfaces import (
    IPricingContextRepository,
    IVariableRepository,
)
from src.modules.pricing.domain.pricing_context import PricingContext
from src.modules.pricing.domain.value_objects import RoundingMode
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateContextCommand:
    context_id: uuid.UUID
    actor_id: uuid.UUID
    expected_version_lock: int | None = None
    name: dict[str, str] | None = None
    rounding_mode: RoundingMode | None = None
    rounding_step: Decimal | None = None
    margin_floor_pct: Decimal | None = None
    evaluation_timeout_ms: int | None = None
    simulation_threshold: int | None = None
    approval_required_on_publish: bool | None = None
    range_base_variable_code: str | None = None
    range_base_variable_code_provided: bool = False
    # Safety net: caller asserts these fields look unchanged. Handler rejects
    # if they differ from the persisted row.
    immutable_attempts: dict[str, object] | None = None


@dataclass(frozen=True)
class UpdateContextResult:
    context_id: uuid.UUID
    code: str
    version_lock: int


_IMMUTABLE_FIELDS = frozenset({"code"})


class UpdateContextHandler:
    def __init__(
        self,
        repo: IPricingContextRepository,
        variable_repo: IVariableRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._variable_repo = variable_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateContextHandler")

    async def handle(self, command: UpdateContextCommand) -> UpdateContextResult:
        async with self._uow:
            ctx = await self._repo.get_by_id(command.context_id)
            if ctx is None:
                raise PricingContextNotFoundError(context_id=command.context_id)

            if command.immutable_attempts:
                self._check_immutables(ctx, command.immutable_attempts)

            if (
                command.expected_version_lock is not None
                and command.expected_version_lock != ctx.version_lock
            ):
                raise PricingContextVersionConflictError(
                    context_id=ctx.id,
                    expected_version=command.expected_version_lock,
                    actual_version=ctx.version_lock,
                )

            if (
                command.range_base_variable_code_provided
                and command.range_base_variable_code is not None
            ):
                variable = await self._variable_repo.get_by_code(
                    command.range_base_variable_code
                )
                if variable is None:
                    raise PricingContextValidationError(
                        message=(
                            f"range_base_variable_code references unknown "
                            f"variable {command.range_base_variable_code!r}."
                        ),
                        error_code="PRICING_CONTEXT_RANGE_BASE_VARIABLE_NOT_FOUND",
                        details={
                            "range_base_variable_code": (
                                command.range_base_variable_code
                            )
                        },
                    )

            ctx.update(
                actor_id=command.actor_id,
                name=command.name,
                rounding_mode=command.rounding_mode,
                rounding_step=command.rounding_step,
                margin_floor_pct=command.margin_floor_pct,
                evaluation_timeout_ms=command.evaluation_timeout_ms,
                simulation_threshold=command.simulation_threshold,
                approval_required_on_publish=command.approval_required_on_publish,
                range_base_variable_code=command.range_base_variable_code,
                range_base_variable_code_provided=(
                    command.range_base_variable_code_provided
                ),
            )
            updated = await self._repo.update(ctx)
            self._uow.register_aggregate(ctx)
            await self._uow.commit()

            self._logger.info(
                "pricing_context_updated",
                context_id=str(updated.id),
                code=updated.code,
                version_lock=updated.version_lock,
            )
            return UpdateContextResult(
                context_id=updated.id,
                code=updated.code,
                version_lock=updated.version_lock,
            )

    @staticmethod
    def _check_immutables(ctx: PricingContext, attempts: dict[str, object]) -> None:
        for field, proposed in attempts.items():
            if field not in _IMMUTABLE_FIELDS:
                continue
            current = getattr(ctx, field)
            if proposed != current:
                raise PricingContextImmutableFieldError(field=field)
