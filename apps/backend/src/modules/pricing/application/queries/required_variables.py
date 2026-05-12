"""Query: list product_input-scope variables required for a product profile.

Returns all variables with ``scope=PRODUCT_INPUT`` from the registry,
annotated with which are ``is_required``. Used by the admin UI form builder
to know which fields must be filled before a product can be priced.

The "resolver up-tree" (inherited required fields from parent categories per
BR-8) is deferred to a future slice; here we return the global registry.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from src.modules.pricing.domain.interfaces import IVariableRepository
from src.modules.pricing.domain.value_objects import VariableScope
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class GetRequiredVariablesQuery:
    product_id: uuid.UUID


@dataclass(frozen=True)
class RequiredVariableReadModel:
    variable_id: uuid.UUID
    code: str
    name: dict[str, str]
    description: dict[str, str] = field(default_factory=dict)
    data_type: str = "decimal"
    unit: str | None = None
    default_value: Decimal | None = None
    is_system: bool = False
    is_required: bool = False


@dataclass(frozen=True)
class GetRequiredVariablesResult:
    product_id: uuid.UUID
    variables: list[RequiredVariableReadModel]


class GetRequiredVariablesHandler:
    """Return all ``product_input``-scope variables from the variable registry.

    These are the variables that must (or can) be filled in a product's
    pricing profile. The result is ordered: required variables first, then
    optional, both sub-sorted by code.
    """

    def __init__(
        self,
        variable_repo: IVariableRepository,
        logger: ILogger,
    ) -> None:
        self._variables = variable_repo
        self._logger = logger.bind(handler="GetRequiredVariablesHandler")

    async def handle(
        self, query: GetRequiredVariablesQuery
    ) -> GetRequiredVariablesResult:
        all_variables = await self._variables.list()
        product_input_vars = [
            v for v in all_variables if v.scope is VariableScope.PRODUCT_INPUT
        ]
        # Required first, then optional; both groups sorted by code.
        product_input_vars.sort(key=lambda v: (not v.is_required, v.code))

        return GetRequiredVariablesResult(
            product_id=query.product_id,
            variables=[
                RequiredVariableReadModel(
                    variable_id=v.id,
                    code=v.code,
                    name=dict(v.name),
                    description=dict(v.description) if v.description else {},
                    data_type=v.data_type.value,
                    unit=v.unit,
                    default_value=v.default_value,
                    is_system=v.is_system,
                    is_required=v.is_required,
                )
                for v in product_input_vars
            ],
        )
