"""Query: preview a product's computed price without persisting.

Wires the pure-domain variable resolver and formula evaluator into an
end-to-end read-side handler. Given a product, its category, and a pricing
context, loads the published :class:`FormulaVersion`, the variable
registry, the product's pricing profile, and the category pricing
settings, resolves all variables, and evaluates the formula.

No I/O-bearing persistence: the result is returned directly to the caller.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from src.modules.pricing.domain.exceptions import FormulaVersionNotFoundError
from src.modules.pricing.domain.formula_evaluator import evaluate_formula
from src.modules.pricing.domain.interfaces import (
    ICategoryPricingSettingsRepository,
    IFormulaVersionRepository,
    IPricingContextRepository,
    IProductPricingProfileRepository,
    ISupplierPricingSettingsRepository,
    IVariableRepository,
)
from src.modules.pricing.domain.variable_resolver import resolve_variables
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class PreviewPriceQuery:
    """Inputs for the price-preview read model."""

    product_id: uuid.UUID
    category_id: uuid.UUID
    context_id: uuid.UUID
    supplier_id: uuid.UUID | None = None


@dataclass(frozen=True)
class PreviewPriceResult:
    """Outputs of a price-preview computation."""

    final_price: Decimal
    components: dict[str, Decimal]
    formula_version_id: uuid.UUID
    formula_version_number: int
    context_id: uuid.UUID


class PreviewPriceHandler:
    """Compute a product's final price on demand (read-only)."""

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
        self._logger = logger.bind(handler="PreviewPriceHandler")

    async def handle(self, query: PreviewPriceQuery) -> PreviewPriceResult:
        formula = await self._formulas.get_published_for_context(query.context_id)
        if formula is None:
            raise FormulaVersionNotFoundError(
                context_id=query.context_id,
                status="published",
            )

        variables = await self._variables.list()
        profile = await self._profiles.get_by_product_id(query.product_id)
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

        resolved = resolve_variables(
            variables,
            product_profile=profile,
            category_settings=settings,
            supplier_settings=supplier_settings,
            context=context,
        )

        evaluation = evaluate_formula(formula.ast, resolved)

        self._logger.info(
            "price_previewed",
            product_id=str(query.product_id),
            category_id=str(query.category_id),
            context_id=str(query.context_id),
            supplier_id=str(query.supplier_id) if query.supplier_id else None,
            formula_version_id=str(formula.id),
            final_price=str(evaluation.final_price),
        )

        return PreviewPriceResult(
            final_price=evaluation.final_price,
            components=evaluation.components,
            formula_version_id=formula.id,
            formula_version_number=formula.version_number,
            context_id=query.context_id,
        )
