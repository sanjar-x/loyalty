"""Create a new ``Variable`` in the registry."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from src.modules.pricing.domain.entities.variable import Variable
from src.modules.pricing.domain.exceptions import VariableCodeTakenError
from src.modules.pricing.domain.interfaces import IVariableRepository
from src.modules.pricing.domain.value_objects import VariableDataType, VariableScope
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateVariableCommand:
    """Input for ``CreateVariableHandler``.

    Attributes:
        code: Unique, lowercase snake_case code (``^[a-z][a-z0-9_]{1,63}$``).
        scope: Immutable scope (where the value lives).
        data_type: Immutable data type.
        unit: Immutable unit string (e.g. ``RUB``, ``RUB/CNY``, ``%``).
        name: i18n label (must include ``ru`` and ``en``).
        description: Optional i18n description.
        is_required: Whether the variable must have a value in its scope.
        default_value: Fallback used when no scope-specific value is set.
        is_system: Flag for system-defined variables (suggests stricter ops).
        is_fx_rate: FX-rate variable (adds freshness-guard semantics).
        max_age_days: Required when ``is_fx_rate=True`` (1–365).
        actor_id: Identity performing the create.
    """

    code: str
    scope: VariableScope
    data_type: VariableDataType
    unit: str
    name: dict[str, str]
    actor_id: uuid.UUID
    description: dict[str, str] | None = None
    is_required: bool = False
    default_value: Decimal | None = None
    is_system: bool = False
    is_fx_rate: bool = False
    max_age_days: int | None = None


@dataclass(frozen=True)
class CreateVariableResult:
    variable_id: uuid.UUID
    code: str
    version_lock: int


class CreateVariableHandler:
    """Register a new ``Variable``."""

    def __init__(
        self,
        repo: IVariableRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateVariableHandler")

    async def handle(self, command: CreateVariableCommand) -> CreateVariableResult:
        async with self._uow:
            existing = await self._repo.get_by_code(command.code)
            if existing is not None:
                raise VariableCodeTakenError(code=command.code)

            variable = Variable.create(
                code=command.code,
                scope=command.scope,
                data_type=command.data_type,
                unit=command.unit,
                name=command.name,
                description=command.description,
                is_required=command.is_required,
                default_value=command.default_value,
                is_system=command.is_system,
                is_fx_rate=command.is_fx_rate,
                max_age_days=command.max_age_days,
                actor_id=command.actor_id,
            )
            await self._repo.add(variable)
            self._uow.register_aggregate(variable)
            await self._uow.commit()

            self._logger.info(
                "pricing_variable_created",
                variable_id=str(variable.id),
                code=variable.code,
                scope=variable.scope.value,
            )
            return CreateVariableResult(
                variable_id=variable.id,
                code=variable.code,
                version_lock=variable.version_lock,
            )
