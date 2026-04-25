"""Anti-corruption reader: pricing-side scope snapshot for one SKU (ADR-005).

Resolves the SKU's pricing context (via ``SupplierTypeContextMapping``),
loads the published formula, the variable registry, and the relevant
category/supplier settings into a single :class:`SkuPricingScopeSnapshot`.
The pure-domain :func:`recompute_sku_pricing` consumes this snapshot
without further I/O.

Stays inside the pricing module — uses only pricing ORM models. No
catalog/supplier imports. The :class:`SkuPricingInputs` argument
already carries ``supplier_type`` (resolved by the catalog reader),
so context lookup is a single mapping query.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.pricing.domain.entities.variable import Variable
from src.modules.pricing.domain.interfaces import (
    ISkuPricingScopeReader,
    SkuPricingInputs,
    SkuPricingScopeSnapshot,
)
from src.modules.pricing.domain.value_objects import VariableDataType, VariableScope
from src.modules.pricing.infrastructure.models import (
    CategoryPricingSettingsModel,
    FormulaVersionModel,
    PricingContextModel,
    SupplierPricingSettingsModel,
    SupplierTypeContextMappingModel,
    VariableModel,
)


class SkuPricingScopeReader(ISkuPricingScopeReader):
    """Materialises ``SkuPricingScopeSnapshot`` for one SKU."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._variables_cache: tuple[Variable, ...] | None = None

    async def snapshot_for_sku(
        self, inputs: SkuPricingInputs
    ) -> SkuPricingScopeSnapshot | None:
        if inputs.supplier_type is None:
            # No supplier_type → no SupplierTypeContextMapping → no
            # pricing context. The recompute service treats this as a
            # configuration gap (admins must wire it).
            return None

        context_id = await self._resolve_context_id(inputs.supplier_type)
        if context_id is None:
            return None

        context = await self._load_context(context_id)
        if context is None:
            return None

        formula = await self._load_published_formula(context_id)
        if formula is None:
            return None

        variables = await self._load_variables()

        category_values = await self._load_category_values(
            category_id=inputs.category_id, context_id=context_id
        )
        supplier_values = await self._load_supplier_values(inputs.supplier_id)

        # ``settings_versions`` is a stable list of (kind, version_lock)
        # tuples — used by ``inputs_hash`` to invalidate cached results
        # whenever any input row was mutated.
        settings_versions = await self._collect_settings_versions(
            category_id=inputs.category_id,
            context_id=context_id,
            supplier_id=inputs.supplier_id,
        )

        return SkuPricingScopeSnapshot(
            context_id=context.id,
            target_currency=_target_currency_for_context(context),
            rounding_mode=context.rounding_mode,
            rounding_step=Decimal(str(context.rounding_step))
            if context.rounding_step is not None
            else None,
            formula_version_id=formula.id,
            formula_version_number=formula.version_number,
            formula_ast=dict(formula.ast or {}),
            evaluation_timeout_ms=context.evaluation_timeout_ms,
            variables=variables,
            global_values={
                k: Decimal(v) for k, v in (context.global_values or {}).items()
            },
            global_value_set_at={
                k: datetime.fromisoformat(v)
                for k, v in (context.global_values_set_at or {}).items()
            },
            category_values=category_values,
            supplier_values=supplier_values,
            settings_versions=settings_versions,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _resolve_context_id(self, supplier_type: str) -> uuid.UUID | None:
        stmt = select(SupplierTypeContextMappingModel.context_id).where(
            SupplierTypeContextMappingModel.supplier_type == supplier_type
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_context(self, context_id: uuid.UUID) -> PricingContextModel | None:
        stmt = select(PricingContextModel).where(
            PricingContextModel.id == context_id,
            PricingContextModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_published_formula(
        self, context_id: uuid.UUID
    ) -> FormulaVersionModel | None:
        # Defensive ORDER BY: a partial unique index on
        # ``(context_id) WHERE status='published'`` should already
        # guarantee at most one published row, but if data drifts
        # ``scalar_one_or_none()`` would raise ``MultipleResultsFound``
        # — instead pick the highest version_number deterministically
        # so ``inputs_hash`` doesn't oscillate between two snapshots.
        stmt = (
            select(FormulaVersionModel)
            .where(
                FormulaVersionModel.context_id == context_id,
                FormulaVersionModel.status == "published",
            )
            .order_by(FormulaVersionModel.version_number.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def _load_variables(self) -> tuple[Variable, ...]:
        if self._variables_cache is not None:
            return self._variables_cache
        stmt = select(VariableModel).order_by(VariableModel.code.asc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        domain_vars = tuple(_variable_to_domain(m) for m in models)
        self._variables_cache = domain_vars
        return domain_vars

    async def _load_category_values(
        self, *, category_id: uuid.UUID, context_id: uuid.UUID
    ) -> dict[str, Decimal]:
        stmt = select(CategoryPricingSettingsModel.values).where(
            CategoryPricingSettingsModel.category_id == category_id,
            CategoryPricingSettingsModel.context_id == context_id,
        )
        result = await self._session.execute(stmt)
        raw = result.scalar_one_or_none() or {}
        return {k: Decimal(v) for k, v in raw.items()}

    async def _load_supplier_values(
        self, supplier_id: uuid.UUID | None
    ) -> dict[str, Decimal]:
        if supplier_id is None:
            return {}
        stmt = select(SupplierPricingSettingsModel.values).where(
            SupplierPricingSettingsModel.supplier_id == supplier_id
        )
        result = await self._session.execute(stmt)
        raw = result.scalar_one_or_none() or {}
        return {k: Decimal(v) for k, v in raw.items()}

    async def _collect_settings_versions(
        self,
        *,
        category_id: uuid.UUID,
        context_id: uuid.UUID,
        supplier_id: uuid.UUID | None,
    ) -> tuple[tuple[str, int], ...]:
        category_v_stmt = select(CategoryPricingSettingsModel.version_lock).where(
            CategoryPricingSettingsModel.category_id == category_id,
            CategoryPricingSettingsModel.context_id == context_id,
        )
        cat_v = (await self._session.execute(category_v_stmt)).scalar_one_or_none()
        sup_v: int | None = None
        if supplier_id is not None:
            sup_v_stmt = select(SupplierPricingSettingsModel.version_lock).where(
                SupplierPricingSettingsModel.supplier_id == supplier_id
            )
            sup_v = (await self._session.execute(sup_v_stmt)).scalar_one_or_none()
        ctx_v_stmt = select(PricingContextModel.version_lock).where(
            PricingContextModel.id == context_id
        )
        ctx_v = (await self._session.execute(ctx_v_stmt)).scalar_one_or_none() or 0
        return (
            ("category", cat_v if cat_v is not None else -1),
            ("supplier", sup_v if sup_v is not None else -1),
            ("context", ctx_v),
        )


def _variable_to_domain(model: VariableModel) -> Variable:
    """Map a ``VariableModel`` row to its domain entity."""
    var = Variable(
        id=model.id,
        code=model.code,
        scope=VariableScope(model.scope),
        data_type=VariableDataType(model.data_type),
        unit=model.unit,
        name=dict(model.name or {}),
        description=dict(model.description or {}),
        is_required=model.is_required,
        default_value=Decimal(model.default_value)
        if model.default_value is not None
        else None,
        is_system=model.is_system,
        is_fx_rate=model.is_fx_rate,
        is_user_editable_at_runtime=False,
        max_age_days=model.max_age_days,
        version_lock=model.version_lock,
        created_at=model.created_at,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
    )
    var.clear_domain_events()
    return var


def _target_currency_for_context(context: PricingContextModel) -> str:
    """The currency in which the context produces selling prices.

    Until the pricing context grows an explicit ``target_currency``
    field the marketplace operates in RUB across the board. Storing
    this as a single source of truth keeps ADR-005 forward-compatible:
    when multi-currency selling lands, only this helper changes.
    """
    del context
    return "RUB"
