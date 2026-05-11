"""Query: preview a SKU's selling price for a hypothetical ``purchase_price``.

Companion to :class:`PreviewPriceHandler`, but accepts a ``purchase_price``
input override so the admin UI can show the formula-computed selling
price *as the operator types* — without persisting the SKU first and
waiting for the autonomous recompute pipeline to land.

The same evaluator + resolver + FX-freshness gate as the recompute
service runs here, so a preview value is by construction equal to
whatever the recompute pipeline would produce for the same inputs
(CAT-013, parity hardened in CAT-017).
"""

from __future__ import annotations

import asyncio
import functools
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.modules.pricing.domain.entities.pricing_context import PricingContext
from src.modules.pricing.domain.entities.variable import Variable
from src.modules.pricing.domain.exceptions import (
    FormulaEvaluationError,
    FormulaVersionNotFoundError,
)
from src.modules.pricing.domain.formula_evaluator import evaluate_formula
from src.modules.pricing.domain.interfaces import (
    ICategoryPricingSettingsRepository,
    IFormulaVersionRepository,
    IPricingContextRepository,
    IProductPricingProfileRepository,
    ISupplierPricingSettingsRepository,
    IVariableRepository,
)
from src.modules.pricing.domain.recompute import (
    PURCHASE_PRICE_CNY_CODE,
    PURCHASE_PRICE_RUB_CODE,
)
from src.modules.pricing.domain.value_objects import VariableScope
from src.modules.pricing.domain.variable_resolver import resolve_variables
from src.shared.exceptions import ValidationError
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class PreviewSkuPricingQuery:
    """Inputs for the SKU-level preview.

    Attributes:
        product_id: Product whose pricing profile supplies
            scope=product_input values (sku_input override happens
            via ``purchase_price_amount`` / ``purchase_currency``).
            ``None`` during the create-product flow when no product
            has been persisted yet — variable resolution falls back
            to ``Variable.default_value`` for product-input scope
            (CAT-022).
        category_id: Category for scope=category values.
        context_id: Pricing context — selects the published formula.
        purchase_price_amount: Hypothetical wholesale cost (smallest
            currency unit). Routed to ``purchase_price_cny`` /
            ``purchase_price_rub`` per ``purchase_currency``.
        purchase_currency: One of ``RUB`` / ``CNY``.
        supplier_id: Optional supplier for scope=supplier overrides.
    """

    category_id: uuid.UUID
    context_id: uuid.UUID
    purchase_price_amount: int
    purchase_currency: str
    product_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None


@dataclass(frozen=True)
class ComponentBreakdown:
    """Human-readable projection of one formula binding's computed value.

    Loyality pricing formulas (FRD §Price Computation) emit a flat
    ``dict[binding_code, Decimal]`` from the evaluator. This breakdown
    row pairs each binding with the operator-facing label stored on
    the binding itself (``label_i18n`` per the v2 AST contract) so
    the admin sees "Цена с доставкой: 50010 ₽" instead of the raw
    snake_case code.

    Attributes:
        code: Machine identifier — formula binding's ``code``
            (snake_case, stable across versions). Persisted on the
            AST so the field never drifts vs the evaluator's keys.
        name: Russian display label sourced from
            ``binding.label_i18n["ru"]``; AST validator guarantees
            non-empty.
        value: Decimal value the evaluator computed for this
            binding.
        is_visible: ``False`` for internal-only intermediate steps
            the formula author chose to hide from the UI (defaults
            to ``True`` for v1 ASTs migrated to v2).
        is_final: ``True`` for the single binding that matches the
            AST's top-level ``final_component_code``.
    """

    code: str
    name: str
    value: Decimal
    is_visible: bool
    is_final: bool


@dataclass(frozen=True)
class PreviewSkuPricingResult:
    """Output of the preview computation."""

    final_price: Decimal
    components: dict[str, Decimal]
    components_breakdown: list[ComponentBreakdown]
    formula_version_id: uuid.UUID
    formula_version_number: int
    context_id: uuid.UUID


class PreviewSkuPricingHandler:
    """Compute a SKU's preview selling price on demand for an admin-supplied
    ``purchase_price``. No persistence; identical evaluator path to the
    autonomous recompute (ADR-005)."""

    def __init__(
        self,
        formula_repo: IFormulaVersionRepository,
        variable_repo: IVariableRepository,
        profile_repo: IProductPricingProfileRepository,
        settings_repo: ICategoryPricingSettingsRepository,
        supplier_settings_repo: ISupplierPricingSettingsRepository,
        context_repo: IPricingContextRepository,
        logger: ILogger,
    ) -> None:
        self._formulas = formula_repo
        self._variables = variable_repo
        self._profiles = profile_repo
        self._settings = settings_repo
        self._supplier_settings = supplier_settings_repo
        self._contexts = context_repo
        self._logger = logger.bind(handler="PreviewSkuPricingHandler")

    async def handle(self, query: PreviewSkuPricingQuery) -> PreviewSkuPricingResult:
        if query.purchase_currency not in ("RUB", "CNY"):
            raise ValidationError(
                message=(
                    f"purchase_currency '{query.purchase_currency}' is not "
                    "supported (use RUB or CNY)"
                ),
                error_code="PRICING_PURCHASE_CURRENCY_UNSUPPORTED",
            )
        if query.purchase_price_amount <= 0:
            raise ValidationError(
                message="purchase_price_amount must be greater than zero",
                error_code="PRICING_PURCHASE_PRICE_INVALID",
            )

        formula = await self._formulas.get_published_for_context(query.context_id)
        if formula is None:
            raise FormulaVersionNotFoundError(
                context_id=query.context_id,
                status="published",
            )

        variables = await self._variables.list()
        # CAT-022 — ``product_id`` is optional during the create-product
        # flow; when absent, variable resolution simply falls back to
        # ``Variable.default_value`` for product_input scope (the
        # admin's "as-you-type" preview is good enough without a
        # persisted profile).
        profile = (
            await self._profiles.get_by_product_id(query.product_id)
            if query.product_id is not None
            else None
        )
        settings = await self._settings.get_by_category_and_context(
            category_id=query.category_id,
            context_id=query.context_id,
        )
        supplier_settings = (
            await self._supplier_settings.get_by_supplier_id(query.supplier_id)
            if query.supplier_id is not None
            else None
        )
        context = await self._contexts.get_by_id(query.context_id)

        # Mirror :func:`recompute._check_fx_freshness` from the autonomous
        # pipeline — without it the preview happily renders a "valid"
        # selling price that the recompute would later reject as
        # ``stale_fx``, breaking the UX promise that "what you see in
        # preview is what lands in the DB" (CAT-017).
        fx_failure_reason = _check_fx_freshness(
            variables, context, now=datetime.now(UTC)
        )
        if fx_failure_reason is not None:
            raise ValidationError(
                message=fx_failure_reason,
                error_code="PRICING_FX_STALE",
                details={"context_id": str(query.context_id)},
            )

        # Same scope sources as recompute, minus the actual SKU read —
        # the resolver below skips ``sku_input`` variables because we
        # inject them manually after.
        sku_input_vars = [v for v in variables if v.scope is VariableScope.SKU_INPUT]
        non_sku_input_vars = [
            v for v in variables if v.scope is not VariableScope.SKU_INPUT
        ]
        resolved = resolve_variables(
            non_sku_input_vars,
            product_profile=profile,
            category_settings=settings,
            supplier_settings=supplier_settings,
            context=context,
        )

        # Inject the SKU's *active* purchase price into the resolved map —
        # mirrors recompute._resolve_variable_values. Only one of the two
        # currency-typed variables is set; the other stays absent so the
        # eager evaluator raises ``PRICING_VARIABLE_MISSING`` if a
        # cross-currency formula references it (which is the same safety
        # rule that protects the autonomous path).
        active_code = (
            PURCHASE_PRICE_RUB_CODE
            if query.purchase_currency == "RUB"
            else PURCHASE_PRICE_CNY_CODE
        )
        # Variable codes registered in DB MUST include the active one;
        # otherwise the formula author hasn't seeded this currency yet.
        if not any(v.code == active_code for v in sku_input_vars):
            raise ValidationError(
                message=(
                    f"sku_input variable '{active_code}' is not registered. "
                    "Seed it via /admin/pricing/variables first."
                ),
                error_code="PRICING_VARIABLE_NOT_REGISTERED",
            )
        resolved[active_code] = Decimal(query.purchase_price_amount)

        timeout_s = (
            context.evaluation_timeout_ms / 1000.0 if context is not None else 1.0
        )
        loop = asyncio.get_running_loop()
        try:
            evaluation = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    functools.partial(evaluate_formula, formula.ast, resolved),
                ),
                timeout=timeout_s,
            )
        except TimeoutError as exc:
            raise FormulaEvaluationError(
                message=(
                    f"Formula evaluation exceeded the configured budget of "
                    f"{int(timeout_s * 1000)}ms."
                ),
                error_code="PRICING_FORMULA_TIMEOUT",
                details={
                    "formula_version_id": str(formula.id),
                    "context_id": str(query.context_id),
                    "timeout_ms": int(timeout_s * 1000),
                },
            ) from exc

        self._logger.info(
            "sku_price_previewed",
            product_id=str(query.product_id) if query.product_id else None,
            context_id=str(query.context_id),
            purchase_price_amount=query.purchase_price_amount,
            purchase_currency=query.purchase_currency,
            final_price=str(evaluation.final_price),
        )

        # Build the labelled breakdown — preserves AST binding order so
        # the admin UI can render "first → last" exactly like the formula
        # author intended (variable resolution → intermediate → final).
        # Labels live on the binding itself per the v2 AST contract.
        components_breakdown = _build_breakdown(
            ast=formula.ast,
            components=evaluation.components,
        )

        return PreviewSkuPricingResult(
            final_price=evaluation.final_price,
            components=evaluation.components,
            components_breakdown=components_breakdown,
            formula_version_id=formula.id,
            formula_version_number=formula.version_number,
            context_id=query.context_id,
        )


_PREFERRED_LABEL_LOCALES: tuple[str, ...] = ("ru", "en")


def _pick_label(label_i18n: dict[str, str], fallback: str) -> str:
    """Pick the operator-facing locale from a binding's ``label_i18n``.

    The v2 AST validator already guarantees a non-empty ``ru`` entry,
    but the picker keeps an ``en`` fallback (post-RS lookup) and a
    last-resort "any value" hop in case a future locale lands without
    a code change.
    """
    for locale in _PREFERRED_LABEL_LOCALES:
        candidate = label_i18n.get(locale)
        if candidate:
            return candidate
    for candidate in label_i18n.values():
        if candidate:
            return candidate
    return fallback


def _build_breakdown(
    *,
    ast: dict,
    components: dict[str, Decimal],
) -> list[ComponentBreakdown]:
    """Pair every evaluated component with its v2 binding metadata.

    Reads ``label_i18n`` / ``is_visible`` directly off each binding —
    no Variable-registry lookup needed (those were v1 heuristics).
    AST validator guarantees these fields exist; we still keep a
    defensive humanised fallback for ASTs that bypassed
    normalisation via direct DB writes.
    """
    bindings = ast.get("bindings") or []
    final_code = ast.get("final_component_code")
    breakdown: list[ComponentBreakdown] = []
    seen: set[str] = set()

    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        code = (
            binding.get("code") or binding.get("component_tag") or binding.get("name")
        )
        if not isinstance(code, str) or code not in components:
            continue
        raw_label = binding.get("label_i18n")
        label = (
            _pick_label(raw_label, fallback=code.replace("_", " ").capitalize())
            if isinstance(raw_label, dict)
            else code.replace("_", " ").capitalize()
        )
        breakdown.append(
            ComponentBreakdown(
                code=code,
                name=label,
                value=components[code],
                is_visible=bool(binding.get("is_visible", True)),
                is_final=code == final_code,
            )
        )
        seen.add(code)

    # Defensive: surface any evaluator-emitted code missing from the
    # AST bindings list (shouldn't happen — evaluator only writes
    # what bindings declared — but the projection should never lose
    # data).
    for code, value in components.items():
        if code in seen:
            continue
        breakdown.append(
            ComponentBreakdown(
                code=code,
                name=code.replace("_", " ").capitalize(),
                value=value,
                is_visible=True,
                is_final=code == final_code,
            )
        )

    return breakdown


def _check_fx_freshness(
    variables: Iterable[Variable],
    context: PricingContext | None,
    *,
    now: datetime,
) -> str | None:
    """Return a stale-FX reason string, or ``None`` when every FX rate is fresh.

    Mirrors the staleness rule applied by
    :func:`src.modules.pricing.domain.recompute._check_fx_freshness`
    so the preview cannot hand the admin a price that the autonomous
    recompute would immediately reject. Decoupled from the
    ``SkuPricingScopeSnapshot`` indirection because the preview path
    already has the underlying ``Variable`` registry + ``PricingContext``
    in hand — replicating the snapshot just for staleness would be
    incidental coupling.
    """
    if context is None:
        # Preview without a context behaves like recompute when scope is
        # missing — surfaces as a configuration error elsewhere; nothing
        # to validate here.
        return None
    for variable in variables:
        if not variable.is_fx_rate:
            continue
        if variable.code not in context.global_values:
            return f"FX rate '{variable.code}' is not configured on the pricing context"
        set_at = context.global_values_set_at.get(variable.code)
        if set_at is None:
            return f"FX rate '{variable.code}' has no recorded set-at timestamp"
        if variable.max_age_days is None:
            continue
        if now - set_at > timedelta(days=variable.max_age_days):
            return (
                f"FX rate '{variable.code}' is older than "
                f"{variable.max_age_days} days "
                f"(set at {set_at.isoformat()})"
            )
    return None
