"""Pure-domain variable resolution service.

Given the ``Variable`` registry plus scope-specific sources (product pricing
profile, category pricing settings, supplier pricing settings, and the pricing
context's global values), produces a flat
``dict[variable_code -> Decimal]`` suitable for feeding into
:func:`~src.modules.pricing.domain.formula_evaluator.evaluate_formula`.

Resolution rules (per ADR-004 + FRD §Variables, BR-8):

======================  =========================================================
``Variable.scope``      Source order
======================  =========================================================
``GLOBAL``              ``context.global_values[code]`` → ``variable.default_value``.
``PRODUCT_INPUT``       ``product_profile.values[code]`` → ``default_value``.
``CATEGORY``            ``category_settings.values[code]`` → ``default_value``.
``SUPPLIER``            ``supplier_settings.values[code]`` → ``default_value``.
``RANGE``               *Deferred (v1)* — falls back to ``default_value``.
======================  =========================================================

If a variable is ``is_required=True`` and nothing resolves, raises
:class:`FormulaEvaluationError` with code ``PRICING_VARIABLE_MISSING``.
Optional variables with no value are omitted from the result; if the formula
references one, the evaluator will raise ``PRICING_VARIABLE_MISSING`` then.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from src.modules.pricing.domain.category_pricing_settings import (
    CategoryPricingSettings,
)
from src.modules.pricing.domain.entities import ProductPricingProfile
from src.modules.pricing.domain.exceptions import FormulaEvaluationError
from src.modules.pricing.domain.pricing_context import PricingContext
from src.modules.pricing.domain.supplier_pricing_settings import (
    SupplierPricingSettings,
)
from src.modules.pricing.domain.value_objects import VariableScope
from src.modules.pricing.domain.variable import Variable


def resolve_variables(
    variables: Iterable[Variable],
    *,
    product_profile: ProductPricingProfile | None = None,
    category_settings: CategoryPricingSettings | None = None,
    supplier_settings: SupplierPricingSettings | None = None,
    context: PricingContext | None = None,
) -> dict[str, Decimal]:
    """Merge scope-specific sources into a single variable-values dict.

    Args:
        variables: The full set of ``Variable`` definitions referenced by
            (or potentially referenced by) the formula. Callers typically
            pass the whole registry or a pre-filtered subset.
        product_profile: Owner of ``scope=product_input`` values. Optional;
            when absent, product-input variables fall back to
            ``variable.default_value``.
        category_settings: Owner of ``scope=category`` values. Optional;
            when absent, category variables fall back to
            ``variable.default_value``.
        supplier_settings: Owner of ``scope=supplier`` values. Optional;
            when absent, supplier variables fall back to
            ``variable.default_value``.
        context: The active ``PricingContext`` for the formula evaluation.
            Its ``global_values`` dict is the primary source for
            ``scope=global`` variables; ``variable.default_value`` is the
            fallback.

    Returns:
        Mapping of variable code → resolved ``Decimal`` value. Variables
        that resolve to nothing (and are not ``is_required``) are omitted.

    Raises:
        FormulaEvaluationError: A required variable has no resolved value.
    """
    profile_values = product_profile.values if product_profile is not None else {}
    category_values = category_settings.values if category_settings is not None else {}
    supplier_values = supplier_settings.values if supplier_settings is not None else {}
    global_values = context.global_values if context is not None else {}

    resolved: dict[str, Decimal] = {}
    for variable in variables:
        value = _resolve_single(
            variable,
            profile_values=profile_values,
            category_values=category_values,
            supplier_values=supplier_values,
            global_values=global_values,
        )
        if value is not None:
            resolved[variable.code] = value
        elif variable.is_required:
            raise FormulaEvaluationError(
                message=(
                    f"Required variable {variable.code!r} (scope="
                    f"{variable.scope.value}) has no resolved value."
                ),
                error_code="PRICING_VARIABLE_MISSING",
                details={
                    "variable": variable.code,
                    "scope": variable.scope.value,
                },
            )
    return resolved


def _resolve_single(
    variable: Variable,
    *,
    profile_values: dict[str, Decimal],
    category_values: dict[str, Decimal],
    supplier_values: dict[str, Decimal],
    global_values: dict[str, Decimal],
) -> Decimal | None:
    scope = variable.scope

    if scope is VariableScope.GLOBAL:
        if variable.code in global_values:
            return global_values[variable.code]
        return variable.default_value

    if scope is VariableScope.PRODUCT_INPUT:
        if variable.code in profile_values:
            return profile_values[variable.code]
        return variable.default_value

    if scope is VariableScope.CATEGORY:
        if variable.code in category_values:
            return category_values[variable.code]
        return variable.default_value

    if scope is VariableScope.SUPPLIER:
        if variable.code in supplier_values:
            return supplier_values[variable.code]
        return variable.default_value

    # RANGE: deferred in v1 — fall back to default_value if the registry
    # carries one, otherwise skip.
    return variable.default_value


__all__ = ["resolve_variables"]
