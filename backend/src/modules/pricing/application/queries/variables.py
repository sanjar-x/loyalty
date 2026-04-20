"""Queries for the ``Variable`` registry."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.modules.pricing.domain.exceptions import VariableNotFoundError
from src.modules.pricing.domain.interfaces import (
    IVariableRepository,
    VariableListFilter,
)
from src.modules.pricing.domain.value_objects import VariableDataType, VariableScope
from src.modules.pricing.domain.variable import Variable


@dataclass(frozen=True)
class VariableReadModel:
    """DTO for a single variable record."""

    variable_id: uuid.UUID
    code: str
    scope: str
    data_type: str
    unit: str
    name: dict[str, str]
    description: dict[str, str]
    is_required: bool
    default_value: Decimal | None
    is_system: bool
    is_fx_rate: bool
    is_user_editable_at_runtime: bool
    max_age_days: int | None
    version_lock: int
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None

    @classmethod
    def from_domain(cls, variable: Variable) -> VariableReadModel:
        return cls(
            variable_id=variable.id,
            code=variable.code,
            scope=variable.scope.value,
            data_type=variable.data_type.value,
            unit=variable.unit,
            name=dict(variable.name),
            description=dict(variable.description),
            is_required=variable.is_required,
            default_value=variable.default_value,
            is_system=variable.is_system,
            is_fx_rate=variable.is_fx_rate,
            is_user_editable_at_runtime=variable.is_user_editable_at_runtime,
            max_age_days=variable.max_age_days,
            version_lock=variable.version_lock,
            created_at=variable.created_at,
            updated_at=variable.updated_at,
            updated_by=variable.updated_by,
        )


@dataclass(frozen=True)
class GetVariableQuery:
    variable_id: uuid.UUID | None = None
    code: str | None = None


@dataclass(frozen=True)
class ListVariablesQuery:
    scope: VariableScope | None = None
    is_system: bool | None = None
    is_fx_rate: bool | None = None


class GetVariableHandler:
    """Fetch a single variable by id or code."""

    def __init__(self, repo: IVariableRepository) -> None:
        self._repo = repo

    async def handle(self, query: GetVariableQuery) -> VariableReadModel:
        if query.variable_id is None and query.code is None:
            raise ValueError("GetVariableQuery requires variable_id or code")
        variable: Variable | None
        if query.variable_id is not None:
            variable = await self._repo.get_by_id(query.variable_id)
        else:
            assert query.code is not None
            variable = await self._repo.get_by_code(query.code)
        if variable is None:
            raise VariableNotFoundError(variable_id=query.variable_id, code=query.code)
        return VariableReadModel.from_domain(variable)


class ListVariablesHandler:
    """List variables with optional filters, ordered by ``code``."""

    def __init__(self, repo: IVariableRepository) -> None:
        self._repo = repo

    async def handle(self, query: ListVariablesQuery) -> list[VariableReadModel]:
        filters = VariableListFilter(
            scope=query.scope,
            is_system=query.is_system,
            is_fx_rate=query.is_fx_rate,
        )
        variables = await self._repo.list(filters)
        return [VariableReadModel.from_domain(v) for v in variables]


__all__ = [
    "GetVariableHandler",
    "GetVariableQuery",
    "ListVariablesHandler",
    "ListVariablesQuery",
    "VariableDataType",
    "VariableReadModel",
    "VariableScope",
]
