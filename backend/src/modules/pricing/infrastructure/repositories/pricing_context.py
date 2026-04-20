"""SQLAlchemy-backed repository for ``PricingContext``."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.pricing.domain.exceptions import (
    PricingContextCodeTakenError,
    PricingContextVersionConflictError,
)
from src.modules.pricing.domain.interfaces import (
    IPricingContextRepository,
    PricingContextListFilter,
)
from src.modules.pricing.domain.pricing_context import PricingContext
from src.modules.pricing.domain.value_objects import RoundingMode
from src.modules.pricing.infrastructure.models import PricingContextModel


def _global_values_to_json(values: dict[str, Decimal]) -> dict[str, str]:
    return {k: str(v) for k, v in values.items()}


def _global_values_from_json(raw: dict) -> dict[str, Decimal]:
    return {k: Decimal(v) for k, v in (raw or {}).items()}


class PricingContextRepository(IPricingContextRepository):
    """Data Mapper repository for the ``PricingContext`` aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(model: PricingContextModel) -> PricingContext:
        ctx = PricingContext(
            id=model.id,
            code=model.code,
            name=dict(model.name or {}),
            is_active=model.is_active,
            is_frozen=model.is_frozen,
            freeze_reason=model.freeze_reason,
            rounding_mode=RoundingMode(model.rounding_mode),
            rounding_step=model.rounding_step,
            margin_floor_pct=model.margin_floor_pct,
            evaluation_timeout_ms=model.evaluation_timeout_ms,
            simulation_threshold=model.simulation_threshold,
            approval_required_on_publish=model.approval_required_on_publish,
            range_base_variable_code=model.range_base_variable_code,
            active_formula_version_id=model.active_formula_version_id,
            global_values=_global_values_from_json(model.global_values),
            version_lock=model.version_lock,
            created_at=model.created_at,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
        )
        ctx.clear_domain_events()
        return ctx

    @staticmethod
    def _apply(model: PricingContextModel, ctx: PricingContext) -> None:
        # ``code`` is immutable; not touched here.
        model.name = dict(ctx.name)
        model.is_active = ctx.is_active
        model.is_frozen = ctx.is_frozen
        model.freeze_reason = ctx.freeze_reason
        model.rounding_mode = ctx.rounding_mode.value
        model.rounding_step = ctx.rounding_step
        model.margin_floor_pct = ctx.margin_floor_pct
        model.evaluation_timeout_ms = ctx.evaluation_timeout_ms
        model.simulation_threshold = ctx.simulation_threshold
        model.approval_required_on_publish = ctx.approval_required_on_publish
        model.range_base_variable_code = ctx.range_base_variable_code
        model.active_formula_version_id = ctx.active_formula_version_id
        model.global_values = _global_values_to_json(ctx.global_values)
        model.version_lock = ctx.version_lock
        model.updated_by = ctx.updated_by

    # ------------------------------------------------------------------
    # Interface methods
    # ------------------------------------------------------------------

    async def add(self, context: PricingContext) -> PricingContext:
        model = PricingContextModel(
            id=context.id,
            code=context.code,
            name=dict(context.name),
            is_active=context.is_active,
            is_frozen=context.is_frozen,
            freeze_reason=context.freeze_reason,
            rounding_mode=context.rounding_mode.value,
            rounding_step=context.rounding_step,
            margin_floor_pct=context.margin_floor_pct,
            evaluation_timeout_ms=context.evaluation_timeout_ms,
            simulation_threshold=context.simulation_threshold,
            approval_required_on_publish=context.approval_required_on_publish,
            range_base_variable_code=context.range_base_variable_code,
            active_formula_version_id=context.active_formula_version_id,
            global_values=_global_values_to_json(context.global_values),
            version_lock=context.version_lock,
            updated_by=context.updated_by,
        )
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise PricingContextCodeTakenError(code=context.code) from exc
        await self._session.refresh(model)
        return self._to_domain(model)

    async def update(self, context: PricingContext) -> PricingContext:
        model = await self._session.get(PricingContextModel, context.id)
        if model is None:
            msg = f"PricingContext {context.id} disappeared before update"
            raise RuntimeError(msg)

        if model.version_lock != context.version_lock - 1:
            raise PricingContextVersionConflictError(
                context_id=context.id,
                expected_version=context.version_lock - 1,
                actual_version=model.version_lock,
            )

        self._apply(model, context)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def get_by_id(self, context_id: uuid.UUID) -> PricingContext | None:
        model = await self._session.get(PricingContextModel, context_id)
        return self._to_domain(model) if model else None

    async def get_by_code(self, code: str) -> PricingContext | None:
        stmt = select(PricingContextModel).where(PricingContextModel.code == code)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list(
        self,
        filters: PricingContextListFilter | None = None,
    ) -> list[PricingContext]:
        stmt = select(PricingContextModel).order_by(PricingContextModel.code.asc())
        if filters is not None:
            if filters.is_active is not None:
                stmt = stmt.where(PricingContextModel.is_active.is_(filters.is_active))
            if filters.is_frozen is not None:
                stmt = stmt.where(PricingContextModel.is_frozen.is_(filters.is_frozen))
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]
