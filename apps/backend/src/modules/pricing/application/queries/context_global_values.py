"""Queries for global-scope variable values stored on a ``PricingContext``."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from src.modules.pricing.domain.exceptions import PricingContextNotFoundError
from src.modules.pricing.domain.interfaces import (
    IPricingContextRepository,
    IVariableRepository,
)
from src.modules.pricing.domain.value_objects import VariableScope
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class GetContextGlobalValuesQuery:
    context_id: uuid.UUID


@dataclass(frozen=True)
class ContextGlobalValueReadModel:
    variable_code: str
    value: Decimal
    variable_name: dict[str, str] = field(default_factory=dict)
    is_required: bool = False


@dataclass(frozen=True)
class GetContextGlobalValuesResult:
    context_id: uuid.UUID
    values: list[ContextGlobalValueReadModel]
    version_lock: int


class GetContextGlobalValuesHandler:
    """Return the global-scope variable values stored on a pricing context.

    Augments each value entry with metadata from the variable registry
    (name, is_required) so callers do not need a second request.
    """

    def __init__(
        self,
        context_repo: IPricingContextRepository,
        variable_repo: IVariableRepository,
        logger: ILogger,
    ) -> None:
        self._contexts = context_repo
        self._variables = variable_repo
        self._logger = logger.bind(handler="GetContextGlobalValuesHandler")

    async def handle(
        self, query: GetContextGlobalValuesQuery
    ) -> GetContextGlobalValuesResult:
        ctx = await self._contexts.get_by_id(query.context_id)
        if ctx is None:
            raise PricingContextNotFoundError(context_id=query.context_id)

        # Build a lookup of all GLOBAL-scope variables for metadata enrichment.
        all_variables = await self._variables.list()
        variable_meta = {
            v.code: v for v in all_variables if v.scope is VariableScope.GLOBAL
        }

        values = [
            ContextGlobalValueReadModel(
                variable_code=code,
                value=value,
                variable_name=dict(variable_meta[code].name)
                if code in variable_meta
                else {},
                is_required=variable_meta[code].is_required
                if code in variable_meta
                else False,
            )
            for code, value in ctx.global_values.items()
        ]

        return GetContextGlobalValuesResult(
            context_id=ctx.id,
            values=values,
            version_lock=ctx.version_lock,
        )
