"""Unit tests for ``CategoryPricingSettings`` aggregate and ``RangeBucket`` VO."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from src.modules.pricing.domain.category_pricing_settings import (
    CategoryPricingSettings,
    RangeBucket,
)
from src.modules.pricing.domain.events import (
    CategoryPricingSettingsCreatedEvent,
    CategoryPricingSettingsDeletedEvent,
    CategoryPricingSettingsUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import (
    CategoryPricingSettingsValidationError,
)

ACTOR = uuid.uuid4()
CATEGORY_ID = uuid.uuid4()
CONTEXT_ID = uuid.uuid4()


def _bucket(
    *,
    min_val: str,
    max_val: str | None,
    values: dict[str, str] | None = None,
) -> RangeBucket:
    return RangeBucket(
        id=uuid.uuid4(),
        min=Decimal(min_val),
        max=None if max_val is None else Decimal(max_val),
        values={k: Decimal(v) for k, v in (values or {}).items()},
    )


def _create(
    *,
    values: dict[str, Decimal] | None = None,
    ranges: list[RangeBucket] | None = None,
    explicit_no_ranges: bool = False,
) -> CategoryPricingSettings:
    return CategoryPricingSettings.create(
        category_id=CATEGORY_ID,
        context_id=CONTEXT_ID,
        values=values or {},
        ranges=ranges or [],
        explicit_no_ranges=explicit_no_ranges,
        actor_id=ACTOR,
    )


# ---------------------------------------------------------------------------
# RangeBucket VO
# ---------------------------------------------------------------------------


class TestRangeBucket:
    def test_valid_closed_bucket(self) -> None:
        b = _bucket(min_val="0", max_val="100")
        assert b.min == Decimal("0")
        assert b.max == Decimal("100")

    def test_valid_open_right_bucket(self) -> None:
        b = _bucket(min_val="100", max_val=None)
        assert b.max is None

    def test_negative_min_rejected(self) -> None:
        with pytest.raises(CategoryPricingSettingsValidationError):
            _bucket(min_val="-1", max_val="10")

    def test_max_le_min_rejected(self) -> None:
        with pytest.raises(CategoryPricingSettingsValidationError):
            _bucket(min_val="100", max_val="100")
        with pytest.raises(CategoryPricingSettingsValidationError):
            _bucket(min_val="100", max_val="50")

    def test_non_snake_case_key_rejected(self) -> None:
        with pytest.raises(CategoryPricingSettingsValidationError):
            RangeBucket(
                id=uuid.uuid4(),
                min=Decimal("0"),
                max=Decimal("10"),
                values={"BadKey": Decimal("1")},
            )


# ---------------------------------------------------------------------------
# Factory .create()
# ---------------------------------------------------------------------------


class TestCreate:
    def test_minimal_create_emits_created_event(self) -> None:
        s = _create()
        assert s.version_lock == 0
        assert s.values == {}
        assert s.ranges == []
        assert s.explicit_no_ranges is False
        events = list(s.domain_events)
        assert len(events) == 1
        assert isinstance(events[0], CategoryPricingSettingsCreatedEvent)
        assert events[0].settings_id == s.id
        assert events[0].range_count == 0

    def test_create_with_values_and_ranges(self) -> None:
        s = _create(
            values={"margin_pct": Decimal("0.25")},
            ranges=[
                _bucket(min_val="0", max_val="100"),
                _bucket(min_val="100", max_val=None, values={"margin_pct": "0.30"}),
            ],
        )
        assert s.values == {"margin_pct": Decimal("0.25")}
        assert len(s.ranges) == 2

    def test_explicit_no_ranges_with_empty_ranges_ok(self) -> None:
        s = _create(explicit_no_ranges=True)
        assert s.explicit_no_ranges is True

    def test_explicit_no_ranges_with_non_empty_ranges_rejected(self) -> None:
        with pytest.raises(CategoryPricingSettingsValidationError):
            _create(
                explicit_no_ranges=True,
                ranges=[_bucket(min_val="0", max_val=None)],
            )

    def test_non_snake_case_values_rejected(self) -> None:
        with pytest.raises(CategoryPricingSettingsValidationError):
            _create(values={"BadCode": Decimal("1")})

    def test_too_many_values_rejected(self) -> None:
        many = {f"code_{i}": Decimal("1") for i in range(129)}
        with pytest.raises(CategoryPricingSettingsValidationError):
            _create(values=many)

    def test_ranges_not_sorted_rejected(self) -> None:
        with pytest.raises(CategoryPricingSettingsValidationError):
            _create(
                ranges=[
                    _bucket(min_val="100", max_val="200"),
                    _bucket(min_val="0", max_val="100"),
                ]
            )

    def test_ranges_with_gap_rejected(self) -> None:
        with pytest.raises(CategoryPricingSettingsValidationError):
            _create(
                ranges=[
                    _bucket(min_val="0", max_val="50"),
                    _bucket(min_val="100", max_val=None),
                ]
            )

    def test_ranges_overlapping_rejected(self) -> None:
        with pytest.raises(CategoryPricingSettingsValidationError):
            _create(
                ranges=[
                    _bucket(min_val="0", max_val="100"),
                    _bucket(min_val="50", max_val="150"),
                ]
            )

    def test_only_last_range_may_have_null_max(self) -> None:
        with pytest.raises(CategoryPricingSettingsValidationError):
            _create(
                ranges=[
                    _bucket(min_val="0", max_val=None),
                    _bucket(min_val="0", max_val="100"),
                ]
            )

    def test_too_many_ranges_rejected(self) -> None:
        ranges: list[RangeBucket] = []
        cursor = Decimal("0")
        for _ in range(65):
            nxt = cursor + Decimal("10")
            ranges.append(
                RangeBucket(
                    id=uuid.uuid4(), min=cursor, max=nxt, values={}
                )
            )
            cursor = nxt
        with pytest.raises(CategoryPricingSettingsValidationError):
            _create(ranges=ranges)

    def test_duplicate_range_ids_rejected(self) -> None:
        shared_id = uuid.uuid4()
        with pytest.raises(CategoryPricingSettingsValidationError):
            _create(
                ranges=[
                    RangeBucket(
                        id=shared_id,
                        min=Decimal("0"),
                        max=Decimal("100"),
                        values={},
                    ),
                    RangeBucket(
                        id=shared_id,
                        min=Decimal("100"),
                        max=None,
                        values={},
                    ),
                ]
            )


# ---------------------------------------------------------------------------
# Mutator .replace()
# ---------------------------------------------------------------------------


class TestReplace:
    def test_replace_bumps_version_and_emits_updated(self) -> None:
        s = _create()
        list(s.domain_events)
        s.clear_domain_events()

        s.replace(
            values={"margin_pct": Decimal("0.3")},
            ranges=[_bucket(min_val="0", max_val=None)],
            explicit_no_ranges=False,
            actor_id=ACTOR,
        )

        assert s.version_lock == 1
        assert s.values == {"margin_pct": Decimal("0.3")}
        assert len(s.ranges) == 1
        events = list(s.domain_events)
        assert len(events) == 1
        assert isinstance(events[0], CategoryPricingSettingsUpdatedEvent)
        assert events[0].range_count == 1

    def test_replace_rejects_invalid_ranges(self) -> None:
        s = _create()
        s.clear_domain_events()

        with pytest.raises(CategoryPricingSettingsValidationError):
            s.replace(
                values={},
                ranges=[
                    _bucket(min_val="100", max_val="200"),
                    _bucket(min_val="0", max_val="100"),
                ],
                explicit_no_ranges=False,
                actor_id=ACTOR,
            )
        assert s.version_lock == 0
        assert list(s.domain_events) == []

    def test_replace_to_empty_with_explicit_flag(self) -> None:
        s = _create(
            ranges=[
                _bucket(min_val="0", max_val="100"),
                _bucket(min_val="100", max_val=None),
            ]
        )
        s.clear_domain_events()

        s.replace(
            values={},
            ranges=[],
            explicit_no_ranges=True,
            actor_id=ACTOR,
        )
        assert s.ranges == []
        assert s.explicit_no_ranges is True
        assert s.version_lock == 1


# ---------------------------------------------------------------------------
# Mutator .mark_deleted()
# ---------------------------------------------------------------------------


class TestMarkDeleted:
    def test_mark_deleted_emits_deleted_event(self) -> None:
        s = _create()
        s.clear_domain_events()

        s.mark_deleted(actor_id=ACTOR)

        events = list(s.domain_events)
        assert len(events) == 1
        assert isinstance(events[0], CategoryPricingSettingsDeletedEvent)
        assert events[0].settings_id == s.id
