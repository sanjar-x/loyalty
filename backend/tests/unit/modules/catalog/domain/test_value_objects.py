# tests/unit/modules/catalog/domain/test_value_objects.py
"""Tests for Catalog domain value objects."""

import pytest

from src.modules.catalog.domain.value_objects import MediaProcessingStatus, Money, ProductStatus

# ---------------------------------------------------------------------------
# MediaProcessingStatus — pre-existing coverage preserved
# ---------------------------------------------------------------------------


def test_media_processing_status_members():
    assert set(MediaProcessingStatus) == {
        MediaProcessingStatus.PENDING_UPLOAD,
        MediaProcessingStatus.PROCESSING,
        MediaProcessingStatus.COMPLETED,
        MediaProcessingStatus.FAILED,
    }


# ---------------------------------------------------------------------------
# ProductStatus — MT-1
# ---------------------------------------------------------------------------


class TestProductStatus:
    """Tests for the ProductStatus domain enum."""

    def test_has_exactly_five_members(self) -> None:
        """ProductStatus must contain exactly 5 lifecycle states."""
        assert len(ProductStatus) == 5

    def test_all_expected_members_present(self) -> None:
        """All five lifecycle states are present."""
        assert set(ProductStatus) == {
            ProductStatus.DRAFT,
            ProductStatus.ENRICHING,
            ProductStatus.READY_FOR_REVIEW,
            ProductStatus.PUBLISHED,
            ProductStatus.ARCHIVED,
        }

    def test_values_are_lowercase_strings(self) -> None:
        """Values must be lowercase strings to match the ORM ProductStatus enum."""
        assert ProductStatus.DRAFT.value == "draft"
        assert ProductStatus.ENRICHING.value == "enriching"
        assert ProductStatus.READY_FOR_REVIEW.value == "ready_for_review"
        assert ProductStatus.PUBLISHED.value == "published"
        assert ProductStatus.ARCHIVED.value == "archived"

    def test_is_str_enum(self) -> None:
        """ProductStatus inherits str — instances compare equal to their string value."""
        assert ProductStatus.DRAFT == "draft"
        assert ProductStatus.PUBLISHED == "published"

    def test_construct_from_string_value(self) -> None:
        """ProductStatus can be reconstructed from its string value."""
        assert ProductStatus("draft") is ProductStatus.DRAFT
        assert ProductStatus("ready_for_review") is ProductStatus.READY_FOR_REVIEW

    @pytest.mark.parametrize(
        "member",
        [
            ProductStatus.DRAFT,
            ProductStatus.ENRICHING,
            ProductStatus.READY_FOR_REVIEW,
            ProductStatus.PUBLISHED,
            ProductStatus.ARCHIVED,
        ],
    )
    def test_each_member_is_a_string(self, member: ProductStatus) -> None:
        """Every member is an instance of str (required for ORM mapping)."""
        assert isinstance(member, str)


# ---------------------------------------------------------------------------
# Money — happy path construction
# ---------------------------------------------------------------------------


class TestMoneyCreation:
    """Tests for valid Money construction."""

    def test_create_with_valid_amount_and_currency(self) -> None:
        """Nominal: valid amount and 3-char currency code succeeds."""
        m = Money(amount=100, currency="RUB")
        assert m.amount == 100
        assert m.currency == "RUB"

    def test_zero_amount_is_valid(self) -> None:
        """Edge case: zero amount is allowed (free items, zero-priced discounts)."""
        m = Money(amount=0, currency="USD")
        assert m.amount == 0

    def test_large_amount_is_valid(self) -> None:
        """Edge case: large integer amounts are accepted without overflow."""
        m = Money(amount=999_999_999, currency="USD")
        assert m.amount == 999_999_999

    @pytest.mark.parametrize("currency", ["RUB", "USD", "EUR", "GBP", "UZS"])
    def test_three_char_currency_codes_accepted(self, currency: str) -> None:
        """Any 3-character string is accepted as currency at the domain level."""
        m = Money(amount=1, currency=currency)
        assert m.currency == currency


# ---------------------------------------------------------------------------
# Money — invalid inputs raise ValueError
# ---------------------------------------------------------------------------


class TestMoneyValidation:
    """Tests for Money construction-time validation."""

    def test_negative_amount_raises_value_error(self) -> None:
        """Invariant: negative amount is rejected."""
        with pytest.raises(ValueError, match="Money amount must be non-negative"):
            Money(amount=-1, currency="RUB")

    def test_large_negative_amount_raises_value_error(self) -> None:
        """Edge: any negative integer is rejected."""
        with pytest.raises(ValueError, match="Money amount must be non-negative"):
            Money(amount=-999, currency="RUB")

    @pytest.mark.parametrize("bad_currency", ["RU", "R", "", "RUBB", "RUBX", "US"])
    def test_currency_not_three_chars_raises_value_error(self, bad_currency: str) -> None:
        """Invariant: currency must be exactly 3 characters."""
        with pytest.raises(ValueError, match="Currency must be a 3-character ISO code"):
            Money(amount=100, currency=bad_currency)

    def test_two_char_currency_raises(self) -> None:
        """Boundary: 2-char currency code is rejected."""
        with pytest.raises(ValueError, match="Currency must be a 3-character ISO code"):
            Money(amount=100, currency="RU")

    def test_four_char_currency_raises(self) -> None:
        """Boundary: 4-char currency code is rejected."""
        with pytest.raises(ValueError, match="Currency must be a 3-character ISO code"):
            Money(amount=100, currency="RUBB")

    def test_empty_currency_raises(self) -> None:
        """Edge: empty string currency is rejected."""
        with pytest.raises(ValueError, match="Currency must be a 3-character ISO code"):
            Money(amount=100, currency="")


# ---------------------------------------------------------------------------
# Money — immutability (frozen attrs)
# ---------------------------------------------------------------------------


class TestMoneyImmutability:
    """Tests for Money frozen value object semantics."""

    def test_amount_cannot_be_mutated(self) -> None:
        """Frozen: assignment to amount must raise FrozenInstanceError."""
        import attrs

        m = Money(amount=100, currency="RUB")
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            m.amount = 200  # type: ignore[misc]

    def test_currency_cannot_be_mutated(self) -> None:
        """Frozen: assignment to currency must raise FrozenInstanceError."""
        import attrs

        m = Money(amount=100, currency="RUB")
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            m.currency = "USD"  # type: ignore[misc]

    def test_money_is_hashable(self) -> None:
        """Frozen attrs classes are hashable — Money can be used in sets/dicts."""
        m1 = Money(amount=100, currency="RUB")
        m2 = Money(amount=100, currency="RUB")
        assert hash(m1) == hash(m2)
        assert len({m1, m2}) == 1


# ---------------------------------------------------------------------------
# Money — equality
# ---------------------------------------------------------------------------


class TestMoneyEquality:
    """Tests for Money equality semantics (attrs-generated __eq__)."""

    def test_equal_same_amount_same_currency(self) -> None:
        """Two Money instances with identical fields are equal."""
        assert Money(amount=100, currency="RUB") == Money(amount=100, currency="RUB")

    def test_not_equal_different_amount(self) -> None:
        """Different amounts with the same currency are not equal."""
        assert Money(amount=100, currency="RUB") != Money(amount=200, currency="RUB")

    def test_not_equal_different_currency(self) -> None:
        """Same amount with different currency codes are not equal."""
        assert Money(amount=100, currency="RUB") != Money(amount=100, currency="USD")

    def test_not_equal_different_amount_and_currency(self) -> None:
        """Different amount and different currency are not equal."""
        assert Money(amount=50, currency="RUB") != Money(amount=100, currency="USD")

    def test_zero_same_currency_equal(self) -> None:
        """Two zero-amount Money with the same currency are equal."""
        assert Money(amount=0, currency="USD") == Money(amount=0, currency="USD")

    def test_zero_different_currency_not_equal(self) -> None:
        """Zero-amount Money in different currencies are not equal."""
        assert Money(amount=0, currency="USD") != Money(amount=0, currency="EUR")


# ---------------------------------------------------------------------------
# Money — same-currency ordering comparisons
# ---------------------------------------------------------------------------


class TestMoneyOrdering:
    """Tests for Money ordering methods with matching currencies."""

    def test_lt_returns_true_when_less(self) -> None:
        """__lt__: smaller amount returns True."""
        assert Money(amount=100, currency="RUB") < Money(amount=200, currency="RUB")

    def test_lt_returns_false_when_greater(self) -> None:
        """__lt__: larger amount returns False."""
        assert not (Money(amount=200, currency="RUB") < Money(amount=100, currency="RUB"))

    def test_lt_returns_false_when_equal(self) -> None:
        """__lt__: equal amounts return False."""
        assert not (Money(amount=100, currency="RUB") < Money(amount=100, currency="RUB"))

    def test_le_returns_true_when_less(self) -> None:
        """__le__: smaller amount returns True."""
        assert Money(amount=100, currency="RUB") <= Money(amount=200, currency="RUB")

    def test_le_returns_true_when_equal(self) -> None:
        """__le__: equal amounts return True."""
        assert Money(amount=100, currency="RUB") <= Money(amount=100, currency="RUB")

    def test_le_returns_false_when_greater(self) -> None:
        """__le__: larger amount returns False."""
        assert not (Money(amount=200, currency="RUB") <= Money(amount=100, currency="RUB"))

    def test_gt_returns_true_when_greater(self) -> None:
        """__gt__: larger amount returns True."""
        assert Money(amount=200, currency="RUB") > Money(amount=100, currency="RUB")

    def test_gt_returns_false_when_equal(self) -> None:
        """__gt__: equal amounts return False."""
        assert not (Money(amount=100, currency="RUB") > Money(amount=100, currency="RUB"))

    def test_gt_returns_false_when_less(self) -> None:
        """__gt__: smaller amount returns False."""
        assert not (Money(amount=100, currency="RUB") > Money(amount=200, currency="RUB"))

    def test_ge_returns_true_when_greater(self) -> None:
        """__ge__: larger amount returns True."""
        assert Money(amount=200, currency="RUB") >= Money(amount=100, currency="RUB")

    def test_ge_returns_true_when_equal(self) -> None:
        """__ge__: equal amounts return True."""
        assert Money(amount=100, currency="RUB") >= Money(amount=100, currency="RUB")

    def test_ge_returns_false_when_less(self) -> None:
        """__ge__: smaller amount returns False."""
        assert not (Money(amount=100, currency="RUB") >= Money(amount=200, currency="RUB"))


# ---------------------------------------------------------------------------
# Money — cross-currency comparison raises ValueError
# ---------------------------------------------------------------------------


class TestMoneyCrossCurrencyComparison:
    """Tests that cross-currency ordering raises ValueError."""

    def test_lt_raises_on_different_currency(self) -> None:
        """__lt__: comparing different currencies raises ValueError."""
        with pytest.raises(ValueError, match="Cannot compare Money with different currencies"):
            _ = Money(amount=100, currency="RUB") < Money(amount=200, currency="USD")

    def test_le_raises_on_different_currency(self) -> None:
        """__le__: comparing different currencies raises ValueError."""
        with pytest.raises(ValueError, match="Cannot compare Money with different currencies"):
            _ = Money(amount=100, currency="RUB") <= Money(amount=100, currency="USD")

    def test_gt_raises_on_different_currency(self) -> None:
        """__gt__: comparing different currencies raises ValueError."""
        with pytest.raises(ValueError, match="Cannot compare Money with different currencies"):
            _ = Money(amount=200, currency="USD") > Money(amount=100, currency="RUB")

    def test_ge_raises_on_different_currency(self) -> None:
        """__ge__: comparing different currencies raises ValueError."""
        with pytest.raises(ValueError, match="Cannot compare Money with different currencies"):
            _ = Money(amount=200, currency="EUR") >= Money(amount=100, currency="RUB")

    def test_error_message_includes_both_currencies(self) -> None:
        """ValueError message names both mismatching currencies for diagnostics."""
        with pytest.raises(ValueError, match="RUB") as exc_info:
            _ = Money(amount=100, currency="RUB") < Money(amount=100, currency="USD")
        assert "USD" in str(exc_info.value)

    @pytest.mark.parametrize(
        "currency_a, currency_b",
        [
            ("RUB", "USD"),
            ("USD", "EUR"),
            ("GBP", "JPY"),
            ("UZS", "KZT"),
        ],
    )
    def test_any_currency_mismatch_raises(self, currency_a: str, currency_b: str) -> None:
        """Any two distinct 3-char currencies raise ValueError on comparison."""
        with pytest.raises(ValueError):
            _ = Money(amount=1, currency=currency_a) < Money(amount=1, currency=currency_b)


# ---------------------------------------------------------------------------
# Money — compare_at_price > price domain invariant (SKU use-case)
# ---------------------------------------------------------------------------


class TestMoneyCompareAtPriceInvariant:
    """Tests illustrating the compare_at_price > price domain rule (MT-2 use-case).

    The Money value object itself does not enforce this rule — it lives in the
    Product/SKU entity. These tests confirm Money provides the comparison
    primitives (lt, gt) that the entity will use.
    """

    def test_compare_at_price_greater_than_price_is_detectable(self) -> None:
        """Domain use-case: compare_at_price=2000 > price=1500 is detectable via gt."""
        price = Money(amount=1500, currency="RUB")
        compare_at_price = Money(amount=2000, currency="RUB")
        assert compare_at_price > price

    def test_compare_at_price_equal_to_price_is_detectable(self) -> None:
        """Domain use-case: compare_at_price == price should be rejected by SKU entity."""
        price = Money(amount=1500, currency="RUB")
        compare_at_price = Money(amount=1500, currency="RUB")
        assert not (compare_at_price > price)

    def test_compare_at_price_less_than_price_is_detectable(self) -> None:
        """Domain use-case: compare_at_price < price should be rejected by SKU entity."""
        price = Money(amount=2000, currency="RUB")
        compare_at_price = Money(amount=1500, currency="RUB")
        assert not (compare_at_price > price)
