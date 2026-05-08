"""Unit tests for the SKU-level price preview query handler (CAT-013).

The preview handler MUST keep parity with the autonomous recompute
pipeline so the admin UI cannot ever show a price the recompute
would later reject. The most important parity rule is FX-rate
freshness — covered by ``TestPreviewSkuFxFreshness`` (CAT-017).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from src.modules.pricing.application.queries.preview_sku_pricing import (
    PreviewSkuPricingHandler,
    PreviewSkuPricingQuery,
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
from src.modules.pricing.domain.interfaces import VariableListFilter
from src.modules.pricing.domain.value_objects import VariableDataType, VariableScope
from src.shared.exceptions import ValidationError


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

    async def add(self, *a: Any, **k: Any) -> Any: ...
    async def update(self, *a: Any, **k: Any) -> Any: ...
    async def delete(self, *a: Any, **k: Any) -> Any: ...
    async def get_by_id(self, *a: Any, **k: Any) -> Any: ...
    async def get_draft_for_context(self, *a: Any, **k: Any) -> Any: ...
    async def list_by_context(self, *a: Any, **k: Any) -> Any: ...
    async def get_max_version_number(self, *a: Any, **k: Any) -> int:
        return 0


class _FakeVariableRepo:
    def __init__(self, variables: Sequence[Variable]) -> None:
        self._variables = variables

    async def list(
        self, filters: VariableListFilter | None = None
    ) -> Sequence[Variable]:
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


def _variable(
    code: str,
    scope: VariableScope,
    *,
    is_required: bool = False,
    default: Decimal | None = None,
    is_fx_rate: bool = False,
    max_age_days: int | None = None,
) -> Variable:
    return Variable.create(
        code=code,
        scope=scope,
        data_type=VariableDataType.DECIMAL,
        unit="RUB",
        name={"ru": code, "en": code},
        is_required=is_required,
        default_value=default,
        is_fx_rate=is_fx_rate,
        max_age_days=max_age_days,
        actor_id=uuid.uuid4(),
    )


def _formula(context_id: uuid.UUID, ast: dict[str, Any]) -> FormulaVersion:
    draft = FormulaVersion.create_draft(
        context_id=context_id,
        version_number=1,
        ast=ast,
        actor_id=uuid.uuid4(),
    )
    draft.publish(actor_id=uuid.uuid4())
    return draft


def _context_with_global(
    *,
    code: str,
    value: Decimal,
    set_at: datetime | None = None,
) -> PricingContext:
    """Build a pricing context with one global value, optionally back-dating
    its ``set_at`` timestamp so we can simulate stale FX rates."""
    ctx = PricingContext.create(
        code=f"ctx_{uuid.uuid4().hex[:8]}",
        name={"ru": "Test", "en": "Test"},
        actor_id=uuid.uuid4(),
    )
    ctx.set_global_value(variable_code=code, value=value, actor_id=uuid.uuid4())
    if set_at is not None:
        # Direct attribute mutation — the entity's setter stamps ``now``,
        # but the staleness rule reads whatever is in ``global_values_set_at``.
        ctx.global_values_set_at = {**ctx.global_values_set_at, code: set_at}
    return ctx


def _build_handler(
    *,
    formula: FormulaVersion | None,
    variables: list[Variable],
    profile: ProductPricingProfile | None = None,
    settings: CategoryPricingSettings | None = None,
    supplier_settings: SupplierPricingSettings | None = None,
    context: PricingContext | None = None,
) -> PreviewSkuPricingHandler:
    return PreviewSkuPricingHandler(
        formula_repo=_FakeFormulaRepo(formula),  # ty: ignore[invalid-argument-type]
        variable_repo=_FakeVariableRepo(variables),  # ty: ignore[invalid-argument-type]
        profile_repo=_FakeProfileRepo(profile),  # ty: ignore[invalid-argument-type]
        settings_repo=_FakeSettingsRepo(settings),  # ty: ignore[invalid-argument-type]
        supplier_settings_repo=_FakeSupplierSettingsRepo(supplier_settings),  # ty: ignore[invalid-argument-type]
        context_repo=_FakeContextRepo(context),  # ty: ignore[invalid-argument-type]
        logger=_FakeLogger(),
    )


def _purchase_price_rub_var() -> Variable:
    """sku_input variable required for the RUB-purchase preview path."""
    return _variable("purchase_price_rub", VariableScope.SKU_INPUT)


# ---------------------------------------------------------------------------
# CAT-017 — FX-freshness parity with the autonomous recompute pipeline
# ---------------------------------------------------------------------------


class TestPreviewSkuFxFreshness:
    """The preview MUST mirror :func:`recompute._check_fx_freshness`.

    Without this gate the admin sees a confidently-rendered price that
    the autonomous pipeline would later reject as ``stale_fx`` —
    breaking the UX promise that "what you see in preview is what
    lands in the DB".
    """

    @pytest.mark.asyncio
    async def test_stale_fx_rate_raises_validation_error(self) -> None:
        context_id = uuid.uuid4()
        # Identity formula so the test isolates the FX gate.
        ast = {
            "version": 1,
            "bindings": [
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {"var": "purchase_price_rub"},
                }
            ],
        }
        fx_var = _variable(
            "cny_to_rub",
            VariableScope.GLOBAL,
            is_fx_rate=True,
            max_age_days=7,
        )
        # Set the rate 30 days ago — well past the 7-day window.
        stale_set_at = datetime.now(UTC) - timedelta(days=30)
        context = _context_with_global(
            code="cny_to_rub",
            value=Decimal("13.50"),
            set_at=stale_set_at,
        )
        handler = _build_handler(
            formula=_formula(context_id, ast),
            variables=[_purchase_price_rub_var(), fx_var],
            context=context,
        )

        with pytest.raises(ValidationError) as exc_info:
            await handler.handle(
                PreviewSkuPricingQuery(
                    product_id=uuid.uuid4(),
                    category_id=uuid.uuid4(),
                    context_id=context_id,
                    purchase_price_amount=10000,
                    purchase_currency="RUB",
                )
            )

        assert exc_info.value.error_code == "PRICING_FX_STALE"
        assert "cny_to_rub" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_fresh_fx_rate_does_not_block_preview(self) -> None:
        context_id = uuid.uuid4()
        ast = {
            "version": 1,
            "bindings": [
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {"var": "purchase_price_rub"},
                }
            ],
        }
        fx_var = _variable(
            "cny_to_rub",
            VariableScope.GLOBAL,
            is_fx_rate=True,
            max_age_days=7,
        )
        # Set 1 day ago — well within the 7-day window.
        fresh_set_at = datetime.now(UTC) - timedelta(days=1)
        context = _context_with_global(
            code="cny_to_rub",
            value=Decimal("13.50"),
            set_at=fresh_set_at,
        )
        handler = _build_handler(
            formula=_formula(context_id, ast),
            variables=[_purchase_price_rub_var(), fx_var],
            context=context,
        )

        result = await handler.handle(
            PreviewSkuPricingQuery(
                product_id=uuid.uuid4(),
                category_id=uuid.uuid4(),
                context_id=context_id,
                purchase_price_amount=10000,
                purchase_currency="RUB",
            )
        )

        assert result.final_price == Decimal("10000")

    @pytest.mark.asyncio
    async def test_fx_rate_without_global_value_blocks_preview(self) -> None:
        """An FX-flagged variable not seeded on the context is treated
        the same as a stale value — recompute would also refuse."""
        context_id = uuid.uuid4()
        ast = {
            "version": 1,
            "bindings": [
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {"var": "purchase_price_rub"},
                }
            ],
        }
        fx_var = _variable(
            "cny_to_rub",
            VariableScope.GLOBAL,
            is_fx_rate=True,
            max_age_days=7,
        )
        # Empty pricing context — no global rate seeded.
        context = PricingContext.create(
            code=f"ctx_{uuid.uuid4().hex[:8]}",
            name={"ru": "Test", "en": "Test"},
            actor_id=uuid.uuid4(),
        )
        handler = _build_handler(
            formula=_formula(context_id, ast),
            variables=[_purchase_price_rub_var(), fx_var],
            context=context,
        )

        with pytest.raises(ValidationError) as exc_info:
            await handler.handle(
                PreviewSkuPricingQuery(
                    product_id=uuid.uuid4(),
                    category_id=uuid.uuid4(),
                    context_id=context_id,
                    purchase_price_amount=10000,
                    purchase_currency="RUB",
                )
            )

        assert exc_info.value.error_code == "PRICING_FX_STALE"
        assert "cny_to_rub" in exc_info.value.message
        assert "not configured" in exc_info.value.message
