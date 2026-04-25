"""Unit tests for the PricingContext aggregate."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from src.modules.pricing.domain.entities.pricing_context import PricingContext
from src.modules.pricing.domain.events import (
    PricingContextCreatedEvent,
    PricingContextDeactivatedEvent,
    PricingContextFrozenEvent,
    PricingContextUnfrozenEvent,
    PricingContextUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import PricingContextValidationError
from src.modules.pricing.domain.value_objects import RoundingMode

ACTOR = uuid.uuid4()


def _make(**overrides: object) -> PricingContext:
    base: dict[str, object] = dict(
        code="retail_ru",
        name={"ru": "Розница РФ", "en": "Retail RU"},
        actor_id=ACTOR,
    )
    base.update(overrides)
    return PricingContext.create(**base)  # type: ignore[arg-type]


@pytest.mark.unit
class TestPricingContextCreate:
    def test_happy_path_emits_created_event(self) -> None:
        ctx = _make()
        assert ctx.code == "retail_ru"
        assert ctx.is_active is True
        assert ctx.is_frozen is False
        assert ctx.freeze_reason is None
        assert ctx.rounding_mode is RoundingMode.HALF_UP
        assert ctx.rounding_step == Decimal("0.01")
        assert ctx.margin_floor_pct == Decimal("0")
        assert ctx.evaluation_timeout_ms == 50
        assert ctx.simulation_threshold == 0
        assert ctx.approval_required_on_publish is False
        assert ctx.range_base_variable_code is None
        assert ctx.active_formula_version_id is None
        assert ctx.version_lock == 0
        assert ctx.updated_by == ACTOR

        events = ctx.domain_events
        assert len(events) == 1
        assert isinstance(events[0], PricingContextCreatedEvent)
        assert events[0].context_id == ctx.id
        assert events[0].code == "retail_ru"
        assert events[0].rounding_mode == "HALF_UP"

    @pytest.mark.parametrize(
        "bad_code",
        ["", "A", "1abc", "foo-bar", "has space", "x" * 65],
    )
    def test_rejects_invalid_code(self, bad_code: str) -> None:
        with pytest.raises(PricingContextValidationError):
            _make(code=bad_code)

    @pytest.mark.parametrize(
        "bad_name",
        [
            {},
            {"ru": "Розница"},
            {"en": "Retail"},
            {"ru": "", "en": "Retail"},
            {"ru": "Розница", "en": "   "},
        ],
    )
    def test_rejects_invalid_name_i18n(self, bad_name: dict[str, str]) -> None:
        with pytest.raises(PricingContextValidationError):
            _make(name=bad_name)

    @pytest.mark.parametrize("step", [Decimal("0"), Decimal("-0.01")])
    def test_rejects_non_positive_rounding_step(self, step: Decimal) -> None:
        with pytest.raises(PricingContextValidationError):
            _make(rounding_step=step)

    @pytest.mark.parametrize(
        "pct", [Decimal("-0.01"), Decimal("1.01"), Decimal("2")]
    )
    def test_rejects_margin_floor_out_of_range(self, pct: Decimal) -> None:
        with pytest.raises(PricingContextValidationError):
            _make(margin_floor_pct=pct)

    @pytest.mark.parametrize("ms", [0, -1, 60_001, 100_000])
    def test_rejects_timeout_out_of_range(self, ms: int) -> None:
        with pytest.raises(PricingContextValidationError):
            _make(evaluation_timeout_ms=ms)

    def test_rejects_negative_simulation_threshold(self) -> None:
        with pytest.raises(PricingContextValidationError):
            _make(simulation_threshold=-1)

    def test_rejects_invalid_range_base_variable_code(self) -> None:
        with pytest.raises(PricingContextValidationError):
            _make(range_base_variable_code="Bad-Code")

    def test_accepts_valid_range_base_variable_code(self) -> None:
        ctx = _make(range_base_variable_code="cost_price")
        assert ctx.range_base_variable_code == "cost_price"


@pytest.mark.unit
class TestPricingContextUpdate:
    def test_update_increments_version_lock_and_emits_event(self) -> None:
        ctx = _make()
        ctx.clear_domain_events()

        ctx.update(
            actor_id=ACTOR,
            rounding_mode=RoundingMode.HALF_EVEN,
            rounding_step=Decimal("0.05"),
            margin_floor_pct=Decimal("0.1"),
            evaluation_timeout_ms=100,
            simulation_threshold=500,
            approval_required_on_publish=True,
        )

        assert ctx.version_lock == 1
        assert ctx.rounding_mode is RoundingMode.HALF_EVEN
        assert ctx.rounding_step == Decimal("0.05")
        assert ctx.margin_floor_pct == Decimal("0.1")
        assert ctx.evaluation_timeout_ms == 100
        assert ctx.simulation_threshold == 500
        assert ctx.approval_required_on_publish is True
        events = ctx.domain_events
        assert len(events) == 1
        assert isinstance(events[0], PricingContextUpdatedEvent)

    def test_update_does_not_touch_code(self) -> None:
        ctx = _make()
        # code isn't a parameter; verify the call signature
        ctx.update(actor_id=ACTOR, name={"ru": "Новое", "en": "New"})
        assert ctx.code == "retail_ru"

    def test_clear_range_base_variable_code_requires_provided_flag(self) -> None:
        ctx = _make(range_base_variable_code="cost_price")
        ctx.clear_domain_events()
        # Without the flag → field is untouched
        ctx.update(actor_id=ACTOR)
        assert ctx.range_base_variable_code == "cost_price"
        # With the flag → cleared
        ctx.update(
            actor_id=ACTOR,
            range_base_variable_code=None,
            range_base_variable_code_provided=True,
        )
        assert ctx.range_base_variable_code is None


@pytest.mark.unit
class TestPricingContextFreeze:
    def test_freeze_sets_flag_and_reason(self) -> None:
        ctx = _make()
        ctx.clear_domain_events()

        ctx.freeze(reason="incident-42 investigation", actor_id=ACTOR)

        assert ctx.is_frozen is True
        assert ctx.freeze_reason == "incident-42 investigation"
        assert ctx.version_lock == 1
        events = ctx.domain_events
        assert len(events) == 1
        assert isinstance(events[0], PricingContextFrozenEvent)

    @pytest.mark.parametrize("bad_reason", ["", "   ", "\n\t"])
    def test_freeze_rejects_empty_reason(self, bad_reason: str) -> None:
        ctx = _make()
        with pytest.raises(PricingContextValidationError):
            ctx.freeze(reason=bad_reason, actor_id=ACTOR)

    def test_unfreeze_clears_reason_and_emits_event(self) -> None:
        ctx = _make()
        ctx.freeze(reason="incident", actor_id=ACTOR)
        ctx.clear_domain_events()

        ctx.unfreeze(actor_id=ACTOR)

        assert ctx.is_frozen is False
        assert ctx.freeze_reason is None
        events = ctx.domain_events
        assert len(events) == 1
        assert isinstance(events[0], PricingContextUnfrozenEvent)


@pytest.mark.unit
class TestPricingContextDeactivate:
    def test_deactivate_sets_flag_and_emits_event(self) -> None:
        ctx = _make()
        ctx.clear_domain_events()

        ctx.deactivate(actor_id=ACTOR)

        assert ctx.is_active is False
        assert ctx.version_lock == 1
        events = ctx.domain_events
        assert len(events) == 1
        assert isinstance(events[0], PricingContextDeactivatedEvent)
