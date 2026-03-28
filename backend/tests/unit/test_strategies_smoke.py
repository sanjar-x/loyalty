"""Smoke tests for Hypothesis strategies.

Validates that each strategy layer produces valid domain instances
that satisfy all invariants. All tests are synchronous (domain entity
construction is purely sync) -- Hypothesis @given does NOT support
async test functions.
"""

from datetime import timedelta

import pytest
from hypothesis import HealthCheck, given, settings

from src.modules.catalog.domain.value_objects import (
    SLUG_RE,
    AttributeDataType,
    MIN_SEARCH_WEIGHT,
    MAX_SEARCH_WEIGHT,
)
from tests.factories.strategies import (
    attribute_groups,
    attributes,
    brands,
    i18n_names,
    money,
    behavior_flags,
    products,
    product_trees,
    root_categories,
    valid_slugs,
)


@pytest.mark.unit
class TestHypothesisStrategies:
    """Smoke tests proving all hypothesis strategies produce valid domain instances."""

    @given(name=i18n_names())
    @settings(max_examples=20, deadline=timedelta(seconds=10))
    def test_i18n_names_always_have_required_locales(self, name: dict[str, str]):
        """i18n_names() always produces dicts with both "ru" and "en" keys
        and non-empty stripped string values."""
        assert "ru" in name
        assert "en" in name
        for locale, value in name.items():
            assert isinstance(value, str)
            assert value.strip() != "", f"Locale '{locale}' has blank value"

    @given(slug=valid_slugs())
    @settings(max_examples=20, deadline=timedelta(seconds=10))
    def test_valid_slugs_match_regex(self, slug: str):
        """valid_slugs() always produces strings matching SLUG_RE."""
        assert SLUG_RE.match(slug) is not None, f"Slug '{slug}' does not match SLUG_RE"

    @given(m=money())
    @settings(max_examples=20, deadline=timedelta(seconds=10))
    def test_money_non_negative(self, m):
        """money() always produces Money with non-negative amount and 3-char currency."""
        assert m.amount >= 0
        assert len(m.currency) == 3

    @given(bf=behavior_flags())
    @settings(max_examples=20, deadline=timedelta(seconds=10))
    def test_behavior_flags_weight_in_range(self, bf):
        """behavior_flags() always produces BehaviorFlags with valid search_weight."""
        assert MIN_SEARCH_WEIGHT <= bf.search_weight <= MAX_SEARCH_WEIGHT

    @given(brand=brands())
    @settings(max_examples=20, deadline=timedelta(seconds=10))
    def test_brand_strategy_produces_valid_brand(self, brand):
        """brands() always produces Brand with non-None id and valid slug."""
        assert brand.id is not None
        assert brand.slug
        assert SLUG_RE.match(brand.slug)

    @given(product=products())
    @settings(max_examples=20, deadline=timedelta(seconds=10))
    def test_product_strategy_has_default_variant(self, product):
        """products() always produces Product with at least one default variant."""
        assert len(product.variants) >= 1

    @given(group=attribute_groups())
    @settings(max_examples=20, deadline=timedelta(seconds=10))
    def test_attribute_group_strategy_valid(self, group):
        """attribute_groups() always produces AttributeGroup with code and id."""
        assert group.code
        assert group.id is not None

    @given(attr=attributes())
    @settings(max_examples=20, deadline=timedelta(seconds=10))
    def test_attribute_strategy_valid(self, attr):
        """attributes() always produces Attribute with valid code, slug, and data_type."""
        assert attr.code
        assert attr.slug
        assert attr.data_type in list(AttributeDataType)

    @given(product=product_trees(max_variants=3))
    @settings(
        max_examples=20,
        deadline=timedelta(seconds=10),
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_product_tree_has_variants(self, product):
        """product_trees() always produces Products with at least 1 variant."""
        assert len(product.variants) >= 1

    @given(cat=root_categories())
    @settings(max_examples=20, deadline=timedelta(seconds=10))
    def test_root_category_strategy_valid(self, cat):
        """root_categories() always produces Category with valid slug and i18n names."""
        assert cat.id is not None
        assert SLUG_RE.match(cat.slug)
        assert "ru" in cat.name_i18n
        assert "en" in cat.name_i18n
