"""Unit tests for the Variable aggregate."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from src.modules.pricing.domain.entities.variable import Variable
from src.modules.pricing.domain.events import (
    VariableCreatedEvent,
    VariableDeletedEvent,
    VariableUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import VariableValidationError
from src.modules.pricing.domain.value_objects import VariableDataType, VariableScope

ACTOR = uuid.uuid4()


def _make(**overrides: object) -> Variable:
    base: dict[str, object] = dict(
        code="cost_price",
        scope=VariableScope.PRODUCT_INPUT,
        data_type=VariableDataType.DECIMAL,
        unit="RUB",
        name={"ru": "Себестоимость", "en": "Cost price"},
        actor_id=ACTOR,
    )
    base.update(overrides)
    return Variable.create(**base)  # ty: ignore[invalid-argument-type]


@pytest.mark.unit
class TestVariableCreate:
    def test_happy_path_emits_created_event(self) -> None:
        var = _make()
        assert var.code == "cost_price"
        assert var.version_lock == 0
        assert var.is_user_editable_at_runtime is False
        events = [e for e in var.domain_events if isinstance(e, VariableCreatedEvent)]
        assert len(events) == 1
        assert events[0].code == "cost_price"

    @pytest.mark.parametrize(
        "bad_code", ["", "A", "1abc", "a", "a" * 65, "foo-bar", "Foo"]
    )
    def test_code_regex_rejects_invalid(self, bad_code: str) -> None:
        with pytest.raises(VariableValidationError):
            _make(code=bad_code)

    @pytest.mark.parametrize("bad_unit", ["", "rub", "1RUB", "RUB!", "R" * 33])
    def test_unit_regex_rejects_invalid(self, bad_unit: str) -> None:
        with pytest.raises(VariableValidationError):
            _make(unit=bad_unit)

    @pytest.mark.parametrize(
        "bad_name",
        [
            {},
            {"ru": "only"},
            {"en": "only"},
            {"ru": "", "en": "ok"},
            {"ru": "ok", "en": ""},
        ],
    )
    def test_name_i18n_requires_ru_and_en(self, bad_name: dict[str, str]) -> None:
        with pytest.raises(VariableValidationError):
            _make(name=bad_name)

    def test_fx_rate_requires_max_age_days(self) -> None:
        with pytest.raises(VariableValidationError):
            _make(is_fx_rate=True, unit="RUB")

    def test_fx_rate_requires_decimal_data_type(self) -> None:
        with pytest.raises(VariableValidationError):
            _make(
                is_fx_rate=True,
                max_age_days=7,
                data_type=VariableDataType.INTEGER,
            )

    def test_non_fx_rejects_max_age_days(self) -> None:
        with pytest.raises(VariableValidationError):
            _make(is_fx_rate=False, max_age_days=7)

    @pytest.mark.parametrize("bad_age", [0, -1, 366])
    def test_fx_max_age_out_of_range(self, bad_age: int) -> None:
        with pytest.raises(VariableValidationError):
            _make(is_fx_rate=True, max_age_days=bad_age)

    def test_default_value_accepts_none(self) -> None:
        var = _make(default_value=None)
        assert var.default_value is None


@pytest.mark.unit
class TestVariableUpdate:
    def test_update_increments_version_and_emits_event(self) -> None:
        var = _make()
        var.clear_domain_events()
        var.update(
            actor_id=ACTOR,
            name={"ru": "Новая", "en": "New"},
            is_required=True,
        )
        assert var.version_lock == 1
        assert var.is_required is True
        events = [e for e in var.domain_events if isinstance(e, VariableUpdatedEvent)]
        assert len(events) == 1

    def test_default_value_provided_true_with_none_clears_value(self) -> None:
        var = _make(default_value=Decimal("10.5"))
        var.update(actor_id=ACTOR, default_value=None, default_value_provided=True)
        assert var.default_value is None

    def test_cannot_drop_max_age_days_on_fx_variable(self) -> None:
        var = _make(
            is_fx_rate=True,
            max_age_days=30,
            unit="RUB",
        )
        with pytest.raises(VariableValidationError):
            var.update(
                actor_id=ACTOR,
                max_age_days=None,
                max_age_days_provided=True,
            )


@pytest.mark.unit
class TestVariableDelete:
    def test_mark_deleted_emits_event(self) -> None:
        var = _make()
        var.clear_domain_events()
        var.mark_deleted(actor_id=ACTOR)
        events = [e for e in var.domain_events if isinstance(e, VariableDeletedEvent)]
        assert len(events) == 1
