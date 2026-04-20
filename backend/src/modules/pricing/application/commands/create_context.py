"""Create a new ``PricingContext``."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from src.modules.pricing.domain.exceptions import PricingContextValidationError
from src.modules.pricing.domain.interfaces import (
    IPricingContextRepository,
    IVariableRepository,
)
from src.modules.pricing.domain.pricing_context import PricingContext
from src.modules.pricing.domain.value_objects import RoundingMode
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateContextCommand:
    code: str
    name: dict[str, str]
    actor_id: uuid.UUID
    rounding_mode: RoundingMode = RoundingMode.HALF_UP
    rounding_step: Decimal = Decimal("0.01")
    margin_floor_pct: Decimal = Decimal("0")
    evaluation_timeout_ms: int = 50
    simulation_threshold: int = 0
    approval_required_on_publish: bool = False
    range_base_variable_code: str | None = None


@dataclass(frozen=True)
class CreateContextResult:
    context_id: uuid.UUID
    code: str
    version_lock: int


class CreateContextHandler:
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
        self._logger = logger.bind(handler="CreateContextHandler")

    async def handle(self, command: CreateContextCommand) -> CreateContextResult:
        async with self._uow:
            if command.range_base_variable_code is not None:
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

            ctx = PricingContext.create(
                code=command.code,
                name=command.name,
                rounding_mode=command.rounding_mode,
                rounding_step=command.rounding_step,
                margin_floor_pct=command.margin_floor_pct,
                evaluation_timeout_ms=command.evaluation_timeout_ms,
                simulation_threshold=command.simulation_threshold,
                approval_required_on_publish=command.approval_required_on_publish,
                range_base_variable_code=command.range_base_variable_code,
                actor_id=command.actor_id,
            )
            self._uow.register_aggregate(ctx)
            saved = await self._repo.add(ctx)
            await self._uow.commit()

            self._logger.info(
                "pricing_context_created",
                context_id=str(saved.id),
                code=saved.code,
            )
            return CreateContextResult(
                context_id=saved.id,
                code=saved.code,
                version_lock=saved.version_lock,
            )
