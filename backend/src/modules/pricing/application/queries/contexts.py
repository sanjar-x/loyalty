"""Queries for the ``PricingContext`` registry."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.modules.pricing.domain.exceptions import PricingContextNotFoundError
from src.modules.pricing.domain.interfaces import (
    IPricingContextRepository,
    PricingContextListFilter,
)
from src.modules.pricing.domain.pricing_context import PricingContext


@dataclass(frozen=True)
class PricingContextReadModel:
    """DTO for a single pricing context."""

    context_id: uuid.UUID
    code: str
    name: dict[str, str]
    is_active: bool
    is_frozen: bool
    freeze_reason: str | None
    rounding_mode: str
    rounding_step: Decimal
    margin_floor_pct: Decimal
    evaluation_timeout_ms: int
    simulation_threshold: int
    approval_required_on_publish: bool
    range_base_variable_code: str | None
    active_formula_version_id: uuid.UUID | None
    version_lock: int
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None

    @classmethod
    def from_domain(cls, ctx: PricingContext) -> PricingContextReadModel:
        return cls(
            context_id=ctx.id,
            code=ctx.code,
            name=dict(ctx.name),
            is_active=ctx.is_active,
            is_frozen=ctx.is_frozen,
            freeze_reason=ctx.freeze_reason,
            rounding_mode=ctx.rounding_mode.value,
            rounding_step=ctx.rounding_step,
            margin_floor_pct=ctx.margin_floor_pct,
            evaluation_timeout_ms=ctx.evaluation_timeout_ms,
            simulation_threshold=ctx.simulation_threshold,
            approval_required_on_publish=ctx.approval_required_on_publish,
            range_base_variable_code=ctx.range_base_variable_code,
            active_formula_version_id=ctx.active_formula_version_id,
            version_lock=ctx.version_lock,
            created_at=ctx.created_at,
            updated_at=ctx.updated_at,
            updated_by=ctx.updated_by,
        )


@dataclass(frozen=True)
class GetContextQuery:
    context_id: uuid.UUID | None = None
    code: str | None = None


@dataclass(frozen=True)
class ListContextsQuery:
    is_active: bool | None = None
    is_frozen: bool | None = None


class GetContextHandler:
    def __init__(self, repo: IPricingContextRepository) -> None:
        self._repo = repo

    async def handle(self, query: GetContextQuery) -> PricingContextReadModel:
        if query.context_id is None and query.code is None:
            raise ValueError("GetContextQuery requires context_id or code")
        ctx: PricingContext | None
        if query.context_id is not None:
            ctx = await self._repo.get_by_id(query.context_id)
        else:
            assert query.code is not None
            ctx = await self._repo.get_by_code(query.code)
        if ctx is None:
            raise PricingContextNotFoundError(
                context_id=query.context_id, code=query.code
            )
        return PricingContextReadModel.from_domain(ctx)


class ListContextsHandler:
    def __init__(self, repo: IPricingContextRepository) -> None:
        self._repo = repo

    async def handle(self, query: ListContextsQuery) -> list[PricingContextReadModel]:
        filters = PricingContextListFilter(
            is_active=query.is_active,
            is_frozen=query.is_frozen,
        )
        contexts = await self._repo.list(filters)
        return [PricingContextReadModel.from_domain(c) for c in contexts]


__all__ = [
    "GetContextHandler",
    "GetContextQuery",
    "ListContextsHandler",
    "ListContextsQuery",
    "PricingContextReadModel",
]
