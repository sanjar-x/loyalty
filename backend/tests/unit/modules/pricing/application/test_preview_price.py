"""Unit tests for the end-to-end price preview query handler."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest

from src.modules.pricing.application.queries.preview_price import (
    PreviewPriceHandler,
    PreviewPriceQuery,
)
from src.modules.pricing.domain.entities import ProductPricingProfile
from src.modules.pricing.domain.entities.category_pricing_settings import (
    CategoryPricingSettings,
)
from src.modules.pricing.domain.entities.formula import FormulaVersion
from src.modules.pricing.domain.entities.pricing_context import PricingContext
from src.modules.pricing.domain.entities.supplier_pricing_settings import (
    SupplierPricingSettings,
)
from src.modules.pricing.domain.entities.variable import Variable
from src.modules.pricing.domain.exceptions import (
    FormulaEvaluationError,
    FormulaVersionNotFoundError,
)
from src.modules.pricing.domain.interfaces import VariableListFilter
from src.modules.pricing.domain.value_objects import VariableDataType, VariableScope

# ---------------------------------------------------------------------------
# Minimal inline fakes — this module has no shared pricing fakes yet.
# ---------------------------------------------------------------------------


class _FakeLogger:
    def bind(self, **_: Any) -> _FakeLogger:
        return self

    def debug(self, *_: Any, **__: Any) -> None: ...
    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...
    def critical(self, *_: Any, **__: Any) -> None: ...


class _FakeFormulaRepo:
    def __init__(self, published: FormulaVersion | None) -> None:
        self._published = published

    async def get_published_for_context(self, context_id: uuid.UUID) -> Any:
        return self._published

    # Unused methods
    async def add(self, *a: Any, **k: Any) -> Any: ...
    async def update(self, *a: Any, **k: Any) -> Any: ...
    async def delete(self, *a: Any, **k: Any) -> Any: ...
    async def get_by_id(self, *a: Any, **k: Any) -> Any: ...
    async def get_draft_for_context(self, *a: Any, **k: Any) -> Any: ...
    async def list_by_context(self, *a: Any, **k: Any) -> Any: ...
    async def get_max_version_number(self, *a: Any, **k: Any) -> int:
        return 0


class _FakeVariableRepo:
    def __init__(self, variables: list[Variable]) -> None:
        self._variables = variables

    async def list(self, filters: VariableListFilter | None = None) -> list[Variable]:
        return list(self._variables)

    async def add(self, *a: Any, **k: Any) -> Any: ...
    async def update(self, *a: Any, **k: Any) -> Any: ...
    async def delete(self, *a: Any, **k: Any) -> Any: ...
    async def get_by_id(self, *a: Any, **k: Any) -> Any: ...
    async def get_by_code(self, *a: Any, **k: Any) -> Any: ...


class _FakeProfileRepo:
    def __init__(self, profile: ProductPricingProfile | None) -> None:
        self._profile = profile

    async def get_by_product_id(
        self, product_id: uuid.UUID, *, include_deleted: bool = False
    ) -> ProductPricingProfile | None:
        return self._profile

    async def add(self, *a: Any, **k: Any) -> Any: ...
    async def update(self, *a: Any, **k: Any) -> Any: ...
    async def delete(self, *a: Any, **k: Any) -> Any: ...
    async def get_by_product_id_for_update(self, *a: Any, **k: Any) -> Any: ...
    async def count_references_to_variable_code(self, *a: Any, **k: Any) -> int:
        return 0


class _FakeSettingsRepo:
    def __init__(self, settings: CategoryPricingSettings | None) -> None:
        self._settings = settings

    async def get_by_category_and_context(
        self, *, category_id: uuid.UUID, context_id: uuid.UUID
    ) -> CategoryPricingSettings | None:
        return self._settings

    async def add(self, *a: Any, **k: Any) -> Any: ...
    async def update(self, *a: Any, **k: Any) -> Any: ...
    async def delete(self, *a: Any, **k: Any) -> Any: ...


class _FakeSupplierSettingsRepo:
    def __init__(self, settings: SupplierPricingSettings | None) -> None:
        self._settings = settings

    async def get_by_supplier_id(
        self, supplier_id: uuid.UUID
    ) -> SupplierPricingSettings | None:
        return self._settings

    async def add(self, *a: Any, **k: Any) -> Any: ...
    async def update(self, *a: Any, **k: Any) -> Any: ...
    async def delete(self, *a: Any, **k: Any) -> Any: ...


class _FakeContextRepo:
    def __init__(self, context: PricingContext | None) -> None:
        self._context = context

    async def get_by_id(self, context_id: uuid.UUID) -> PricingContext | None:
        return self._context

    async def add(self, *a: Any, **k: Any) -> Any: ...
    async def update(self, *a: Any, **k: Any) -> Any: ...
    async def get_by_code(self, *a: Any, **k: Any) -> Any: ...
    async def list(self, *a: Any, **k: Any) -> Any: ...


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------


def _variable(
    code: str,
    scope: VariableScope,
    *,
    is_required: bool = False,
    default: Decimal | None = None,
) -> Variable:
    return Variable.create(
        code=code,
        scope=scope,
        data_type=VariableDataType.DECIMAL,
        unit="RUB",
        name={"ru": code, "en": code},
        is_required=is_required,
        default_value=default,
        actor_id=uuid.uuid4(),
    )


def _formula(context_id: uuid.UUID, ast: dict[str, Any]) -> FormulaVersion:
    # Build a published formula via create_draft + publish path.
    draft = FormulaVersion.create_draft(
        context_id=context_id,
        version_number=1,
        ast=ast,
        actor_id=uuid.uuid4(),
    )
    draft.publish(actor_id=uuid.uuid4())
    return draft


def _profile(
    product_id: uuid.UUID, values: dict[str, Decimal]
) -> ProductPricingProfile:
    return ProductPricingProfile.create(
        product_id=product_id,
        values=values,
        actor_id=uuid.uuid4(),
    )


def _settings(
    category_id: uuid.UUID,
    context_id: uuid.UUID,
    values: dict[str, Decimal],
) -> CategoryPricingSettings:
    return CategoryPricingSettings.create(
        category_id=category_id,
        context_id=context_id,
        values=values,
        ranges=[],
        explicit_no_ranges=True,
        actor_id=uuid.uuid4(),
    )


def _supplier_settings(
    supplier_id: uuid.UUID,
    values: dict[str, Decimal],
) -> SupplierPricingSettings:
    return SupplierPricingSettings.create(
        supplier_id=supplier_id,
        values=values,
        actor_id=uuid.uuid4(),
    )


def _context(global_values: dict[str, Decimal]) -> PricingContext:
    ctx = PricingContext.create(
        code=f"ctx_{uuid.uuid4().hex[:8]}",
        name={"ru": "Test", "en": "Test"},
        actor_id=uuid.uuid4(),
    )
    for code, value in global_values.items():
        ctx.set_global_value(variable_code=code, value=value, actor_id=uuid.uuid4())
    return ctx


def _build_handler(
    *,
    formula: FormulaVersion | None,
    variables: list[Variable],
    profile: ProductPricingProfile | None = None,
    settings: CategoryPricingSettings | None = None,
    supplier_settings: SupplierPricingSettings | None = None,
    context: PricingContext | None = None,
) -> PreviewPriceHandler:
    return PreviewPriceHandler(
        formula_repo=_FakeFormulaRepo(formula),  # type: ignore[arg-type]
        variable_repo=_FakeVariableRepo(variables),  # type: ignore[arg-type]
        profile_repo=_FakeProfileRepo(profile),  # type: ignore[arg-type]
        settings_repo=_FakeSettingsRepo(settings),  # type: ignore[arg-type]
        supplier_settings_repo=_FakeSupplierSettingsRepo(supplier_settings),  # type: ignore[arg-type]
        context_repo=_FakeContextRepo(context),  # type: ignore[arg-type]
        logger=_FakeLogger(),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPreviewPriceHandler:
    @pytest.mark.asyncio
    async def test_end_to_end_computes_price(self) -> None:
        product_id, category_id, context_id = (
            uuid.uuid4(),
            uuid.uuid4(),
            uuid.uuid4(),
        )
        ast = {
            "version": 1,
            "bindings": [
                {
                    "name": "markup",
                    "component_tag": "component",
                    "expr": {
                        "op": "*",
                        "args": [
                            {"var": "cost"},
                            {
                                "op": "+",
                                "args": [{"const": "1"}, {"var": "margin_pct"}],
                            },
                        ],
                    },
                },
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {
                        "op": "*",
                        "args": [
                            {"ref": "markup"},
                            {"op": "+", "args": [{"const": "1"}, {"var": "vat_pct"}]},
                        ],
                    },
                },
            ],
        }
        variables = [
            _variable(
                "cost",
                VariableScope.PRODUCT_INPUT,
                is_required=True,
            ),
            _variable(
                "margin_pct",
                VariableScope.CATEGORY,
                default=Decimal("0.20"),
            ),
            _variable(
                "vat_pct",
                VariableScope.GLOBAL,
                default=Decimal("0.12"),
            ),
        ]
        handler = _build_handler(
            formula=_formula(context_id, ast),
            variables=variables,
            profile=_profile(product_id, {"cost": Decimal("100")}),
            settings=_settings(category_id, context_id, {}),
        )

        result = await handler.handle(
            PreviewPriceQuery(
                product_id=product_id,
                category_id=category_id,
                context_id=context_id,
            )
        )

        assert result.final_price == Decimal("134.4000")
        assert result.components["markup"] == Decimal("120.00")
        assert result.formula_version_number == 1
        assert result.context_id == context_id

    @pytest.mark.asyncio
    async def test_missing_published_formula_raises(self) -> None:
        handler = _build_handler(formula=None, variables=[])
        with pytest.raises(FormulaVersionNotFoundError):
            await handler.handle(
                PreviewPriceQuery(
                    product_id=uuid.uuid4(),
                    category_id=uuid.uuid4(),
                    context_id=uuid.uuid4(),
                )
            )

    @pytest.mark.asyncio
    async def test_missing_required_variable_raises(self) -> None:
        context_id = uuid.uuid4()
        ast = {
            "version": 1,
            "bindings": [
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {"var": "cost"},
                }
            ],
        }
        handler = _build_handler(
            formula=_formula(context_id, ast),
            variables=[
                _variable("cost", VariableScope.PRODUCT_INPUT, is_required=True)
            ],
            profile=None,
        )
        with pytest.raises(FormulaEvaluationError) as exc:
            await handler.handle(
                PreviewPriceQuery(
                    product_id=uuid.uuid4(),
                    category_id=uuid.uuid4(),
                    context_id=context_id,
                )
            )
        assert exc.value.error_code == "PRICING_VARIABLE_MISSING"

    @pytest.mark.asyncio
    async def test_works_without_profile_or_settings(self) -> None:
        # Formula uses only GLOBAL-scope vars; no profile/settings needed.
        context_id = uuid.uuid4()
        ast = {
            "version": 1,
            "bindings": [
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {
                        "op": "*",
                        "args": [{"var": "fx_usd"}, {"const": "10"}],
                    },
                }
            ],
        }
        handler = _build_handler(
            formula=_formula(context_id, ast),
            variables=[
                _variable(
                    "fx_usd", VariableScope.GLOBAL, default=Decimal("92.5")
                )
            ],
        )
        result = await handler.handle(
            PreviewPriceQuery(
                product_id=uuid.uuid4(),
                category_id=uuid.uuid4(),
                context_id=context_id,
            )
        )
        assert result.final_price == Decimal("925.0")

    @pytest.mark.asyncio
    async def test_supplier_scope_uses_settings_values(self) -> None:
        """SUPPLIER-scope variable is resolved from SupplierPricingSettings."""
        context_id = uuid.uuid4()
        supplier_id = uuid.uuid4()
        ast = {
            "version": 1,
            "bindings": [
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {
                        "op": "*",
                        "args": [{"var": "cost"}, {"var": "supplier_markup"}],
                    },
                }
            ],
        }
        variables = [
            _variable("cost", VariableScope.PRODUCT_INPUT, is_required=True),
            _variable(
                "supplier_markup",
                VariableScope.SUPPLIER,
                default=Decimal("1.10"),
            ),
        ]
        sup_settings = _supplier_settings(
            supplier_id, {"supplier_markup": Decimal("1.30")}
        )
        product_id = uuid.uuid4()
        handler = _build_handler(
            formula=_formula(context_id, ast),
            variables=variables,
            profile=_profile(product_id, {"cost": Decimal("100")}),
            supplier_settings=sup_settings,
        )

        result = await handler.handle(
            PreviewPriceQuery(
                product_id=product_id,
                category_id=uuid.uuid4(),
                context_id=context_id,
                supplier_id=supplier_id,
            )
        )
        # 100 * 1.30 = 130
        assert result.final_price == Decimal("130.00")

    @pytest.mark.asyncio
    async def test_supplier_scope_falls_back_to_default_when_no_supplier_id(
        self,
    ) -> None:
        """When no supplier_id in query, SUPPLIER vars use default_value."""
        context_id = uuid.uuid4()
        ast = {
            "version": 1,
            "bindings": [
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {"var": "supplier_markup"},
                }
            ],
        }
        variables = [
            _variable(
                "supplier_markup",
                VariableScope.SUPPLIER,
                default=Decimal("1.10"),
            )
        ]
        handler = _build_handler(
            formula=_formula(context_id, ast),
            variables=variables,
        )

        result = await handler.handle(
            PreviewPriceQuery(
                product_id=uuid.uuid4(),
                category_id=uuid.uuid4(),
                context_id=context_id,
                # supplier_id omitted
            )
        )
        assert result.final_price == Decimal("1.10")

    @pytest.mark.asyncio
    async def test_global_scope_uses_context_override(self) -> None:
        """BR-8: context.global_values[code] overrides default in preview."""
        context_id = uuid.uuid4()
        ast = {
            "version": 1,
            "bindings": [
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {
                        "op": "*",
                        "args": [{"var": "fx_usd"}, {"const": "10"}],
                    },
                }
            ],
        }
        variables = [
            _variable("fx_usd", VariableScope.GLOBAL, default=Decimal("92.5"))
        ]
        ctx = _context({"fx_usd": Decimal("100.0")})
        handler = _build_handler(
            formula=_formula(context_id, ast),
            variables=variables,
            context=ctx,
        )
        result = await handler.handle(
            PreviewPriceQuery(
                product_id=uuid.uuid4(),
                category_id=uuid.uuid4(),
                context_id=context_id,
            )
        )
        # 100.0 * 10 = 1000.0 (not 925.0 from default)
        assert result.final_price == Decimal("1000.0")
