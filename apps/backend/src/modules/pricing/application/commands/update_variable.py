"""Update the mutable subset of a ``Variable``."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from src.modules.pricing.domain.entities.variable import Variable
from src.modules.pricing.domain.exceptions import (
    VariableImmutableFieldError,
    VariableNotFoundError,
    VariableValidationError,
)
from src.modules.pricing.domain.interfaces import IVariableRepository
from src.modules.pricing.domain.value_objects import VariableDataType, VariableScope
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateVariableCommand:
    """Input for ``UpdateVariableHandler``.

    Mutable fields: ``name``, ``description``, ``is_required``,
    ``default_value``, ``max_age_days``. Any other field present in
    ``immutable_attempts`` triggers ``VariableImmutableFieldError``.

    The ``*_provided`` flags distinguish "caller intentionally sets to None"
    from "caller didn't touch this field".
    """

    variable_id: uuid.UUID
    actor_id: uuid.UUID
    expected_version_lock: int | None = None
    name: dict[str, str] | None = None
    description: dict[str, str] | None = None
    is_required: bool | None = None
    default_value: Decimal | None = None
    default_value_provided: bool = False
    max_age_days: int | None = None
    max_age_days_provided: bool = False
    # If set, the handler verifies these would-be-immutable values match the
    # persisted row and rejects otherwise (front-end safety net).
    immutable_attempts: dict[str, object] | None = None


@dataclass(frozen=True)
class UpdateVariableResult:
    variable_id: uuid.UUID
    code: str
    version_lock: int


_IMMUTABLE_FIELDS = frozenset({"code", "scope", "data_type", "unit", "is_fx_rate"})


class UpdateVariableHandler:
    """Update the mutable subset of a ``Variable``."""

    def __init__(
        self,
        repo: IVariableRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateVariableHandler")

    async def handle(self, command: UpdateVariableCommand) -> UpdateVariableResult:
        async with self._uow:
            variable = await self._repo.get_by_id(command.variable_id)
            if variable is None:
                raise VariableNotFoundError(variable_id=command.variable_id)

            if command.immutable_attempts:
                self._check_immutables(variable, command.immutable_attempts)

            if (
                command.expected_version_lock is not None
                and command.expected_version_lock != variable.version_lock
            ):
                raise VariableValidationError(
                    message=(
                        "Variable was modified concurrently; expected version "
                        f"{command.expected_version_lock}, got {variable.version_lock}."
                    ),
                    error_code="PRICING_VARIABLE_VERSION_CONFLICT",
                    details={
                        "variable_id": str(command.variable_id),
                        "expected_version": command.expected_version_lock,
                        "actual_version": variable.version_lock,
                    },
                )

            variable.update(
                actor_id=command.actor_id,
                name=command.name,
                description=command.description,
                is_required=command.is_required,
                default_value=command.default_value,
                default_value_provided=command.default_value_provided,
                max_age_days=command.max_age_days,
                max_age_days_provided=command.max_age_days_provided,
            )
            updated = await self._repo.update(variable)
            self._uow.register_aggregate(variable)
            await self._uow.commit()

            self._logger.info(
                "pricing_variable_updated",
                variable_id=str(updated.id),
                code=updated.code,
                version_lock=updated.version_lock,
            )
            return UpdateVariableResult(
                variable_id=updated.id,
                code=updated.code,
                version_lock=updated.version_lock,
            )

    @staticmethod
    def _check_immutables(variable: Variable, attempts: dict[str, object]) -> None:
        for field, proposed in attempts.items():
            if field not in _IMMUTABLE_FIELDS:
                continue
            current = _current_immutable_value(variable, field)
            if proposed != current:
                raise VariableImmutableFieldError(field=field)


def _current_immutable_value(variable: Variable, field: str) -> object:
    value = getattr(variable, field)
    if isinstance(value, (VariableScope, VariableDataType)):
        return value.value
    return value
