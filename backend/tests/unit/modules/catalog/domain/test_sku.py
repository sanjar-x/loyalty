# tests/unit/modules/catalog/domain/test_sku.py
"""Unit tests for the SKU child entity domain class (MT-2)."""

import uuid
from datetime import UTC, datetime

import pytest

from src.modules.catalog.domain.entities import SKU
from src.modules.catalog.domain.value_objects import Money
from src.shared.interfaces.entities import AggregateRoot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_money(amount: int = 10_000, currency: str = "RUB") -> Money:
    """Create a Money value object for testing."""
    return Money(amount=amount, currency=currency)


def make_sku(
    product_id: uuid.UUID | None = None,
    sku_code: str = "SKU-001",
    price: Money | None = None,
    compare_at_price: Money | None = None,
    variant_hash: str | None = None,
    is_active: bool = True,
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] | None = None,
) -> SKU:
    """Create a minimal valid SKU for testing."""
    return SKU(
        id=uuid.uuid4(),
        product_id=product_id or uuid.uuid4(),
        sku_code=sku_code,
        variant_hash=variant_hash or "a" * 64,
        price=price or make_money(),
        compare_at_price=compare_at_price,
        is_active=is_active,
        variant_attributes=variant_attributes or [],
    )


# ---------------------------------------------------------------------------
# SKU construction / post-init validation
# ---------------------------------------------------------------------------


class TestSKUCreation:
    """Tests for SKU field initialization and __attrs_post_init__ validation."""

    def test_sku_stores_all_fields(self) -> None:
        """Nominal: all fields are stored as supplied."""
        pid = uuid.uuid4()
        sid = uuid.uuid4()
        price = Money(amount=3000, currency="USD")
        compare = Money(amount=5000, currency="USD")
        a_id, v_id = uuid.uuid4(), uuid.uuid4()
        sku = SKU(
            id=sid,
            product_id=pid,
            sku_code="MYSKU",
            variant_hash="b" * 64,
            price=price,
            compare_at_price=compare,
            is_active=False,
            version=3,
            variant_attributes=[(a_id, v_id)],
        )
        assert sku.id == sid
        assert sku.product_id == pid
        assert sku.sku_code == "MYSKU"
        assert sku.variant_hash == "b" * 64
        assert sku.price == price
        assert sku.compare_at_price == compare
        assert sku.is_active is False
        assert sku.version == 3
        assert sku.variant_attributes == [(a_id, v_id)]

    def test_sku_defaults_is_active_to_true(self) -> None:
        """Default is_active is True."""
        sku = make_sku()
        assert sku.is_active is True

    def test_sku_defaults_version_to_one(self) -> None:
        """Default version is 1."""
        sku = make_sku()
        assert sku.version == 1

    def test_sku_defaults_deleted_at_to_none(self) -> None:
        """Default deleted_at is None (active)."""
        sku = make_sku()
        assert sku.deleted_at is None

    def test_sku_defaults_compare_at_price_to_none(self) -> None:
        """Default compare_at_price is None (no strikethrough price)."""
        sku = make_sku()
        assert sku.compare_at_price is None

    def test_sku_defaults_variant_attributes_to_empty_list(self) -> None:
        """Default variant_attributes is an empty list."""
        sku = make_sku()
        assert sku.variant_attributes == []

    def test_sku_sets_created_at_to_now(self) -> None:
        """created_at is set to a recent UTC timestamp on construction."""
        before = datetime.now(UTC)
        sku = make_sku()
        after = datetime.now(UTC)
        assert before <= sku.created_at <= after

    def test_sku_sets_updated_at_to_now(self) -> None:
        """updated_at is set to a recent UTC timestamp on construction."""
        before = datetime.now(UTC)
        sku = make_sku()
        after = datetime.now(UTC)
        assert before <= sku.updated_at <= after

    def test_sku_is_not_aggregate_root(self) -> None:
        """SKU must NOT extend AggregateRoot — it is a child entity."""
        sku = make_sku()
        assert not isinstance(sku, AggregateRoot)

    def test_variant_attributes_list_is_independent_per_instance(self) -> None:
        """Risk: field(factory=list) must give each SKU its own list."""
        sku1 = make_sku()
        sku2 = make_sku()
        sku1.variant_attributes.append((uuid.uuid4(), uuid.uuid4()))
        assert sku2.variant_attributes == []

    # --- compare_at_price validation in __attrs_post_init__ ---

    def test_compare_at_price_greater_than_price_is_valid(self) -> None:
        """compare_at_price > price is accepted without error."""
        price = Money(amount=3000, currency="RUB")
        compare = Money(amount=5000, currency="RUB")
        sku = make_sku(price=price, compare_at_price=compare)
        assert sku.compare_at_price == compare

    def test_compare_at_price_equal_to_price_raises(self) -> None:
        """compare_at_price == price must raise ValueError at construction."""
        price = Money(amount=5000, currency="RUB")
        with pytest.raises(ValueError, match="compare_at_price must be greater than price"):
            make_sku(price=price, compare_at_price=price)

    def test_compare_at_price_less_than_price_raises(self) -> None:
        """compare_at_price < price must raise ValueError at construction."""
        price = Money(amount=5000, currency="RUB")
        lower = Money(amount=2000, currency="RUB")
        with pytest.raises(ValueError, match="compare_at_price must be greater than price"):
            make_sku(price=price, compare_at_price=lower)

    def test_compare_at_price_none_skips_validation(self) -> None:
        """compare_at_price=None skips the > price validation."""
        sku = make_sku(compare_at_price=None)
        assert sku.compare_at_price is None

    def test_compare_at_price_different_currency_raises(self) -> None:
        """Cross-currency comparison raises ValueError from Money._check_currency."""
        price = Money(amount=3000, currency="RUB")
        compare = Money(amount=5000, currency="USD")
        with pytest.raises(ValueError):
            make_sku(price=price, compare_at_price=compare)

    @pytest.mark.parametrize(
        "price_amount, compare_amount",
        [
            (1, 1),  # equal
            (1000, 500),  # compare < price
            (0, 0),  # both zero
        ],
    )
    def test_compare_at_price_invalid_cases(self, price_amount: int, compare_amount: int) -> None:
        """Parametrize: all non-strictly-greater compare_at_price values are rejected."""
        price = Money(amount=price_amount, currency="RUB")
        compare = Money(amount=compare_amount, currency="RUB")
        with pytest.raises(ValueError):
            make_sku(price=price, compare_at_price=compare)


# ---------------------------------------------------------------------------
# SKU.soft_delete()
# ---------------------------------------------------------------------------


class TestSKUSoftDelete:
    """Tests for SKU.soft_delete() method."""

    def test_soft_delete_sets_deleted_at(self) -> None:
        """soft_delete() stamps deleted_at with current UTC time."""
        sku = make_sku()
        assert sku.deleted_at is None
        before = datetime.now(UTC)
        sku.soft_delete()
        after = datetime.now(UTC)
        assert sku.deleted_at is not None
        assert before <= sku.deleted_at <= after

    def test_soft_delete_sets_updated_at(self) -> None:
        """soft_delete() also advances updated_at."""
        sku = make_sku()
        before = datetime.now(UTC)
        sku.soft_delete()
        after = datetime.now(UTC)
        assert before <= sku.updated_at <= after

    def test_soft_delete_does_not_clear_other_fields(self) -> None:
        """soft_delete() only touches deleted_at and updated_at."""
        sku = make_sku(sku_code="KEEP-ME", price=make_money(5000))
        sku.soft_delete()
        assert sku.sku_code == "KEEP-ME"
        assert sku.price == make_money(5000)
        assert sku.is_active is True  # is_active is not changed by soft_delete


# ---------------------------------------------------------------------------
# SKU.update()
# ---------------------------------------------------------------------------


class TestSKUUpdate:
    """Tests for SKU.update() method."""

    def test_update_sku_code(self) -> None:
        """update() replaces sku_code when provided."""
        sku = make_sku(sku_code="OLD")
        sku.update(sku_code="NEW")
        assert sku.sku_code == "NEW"

    def test_update_price(self) -> None:
        """update() replaces price when provided."""
        sku = make_sku(price=make_money(1000))
        new_price = make_money(2000)
        sku.update(price=new_price)
        assert sku.price == new_price

    def test_update_is_active(self) -> None:
        """update() replaces is_active when provided."""
        sku = make_sku(is_active=True)
        sku.update(is_active=False)
        assert sku.is_active is False

    def test_update_variant_attributes(self) -> None:
        """update() replaces variant_attributes when provided."""
        sku = make_sku(variant_attributes=[])
        new_pairs = [(uuid.uuid4(), uuid.uuid4())]
        sku.update(variant_attributes=new_pairs)
        assert sku.variant_attributes == new_pairs

    def test_update_variant_hash(self) -> None:
        """update() replaces variant_hash when provided."""
        sku = make_sku(variant_hash="a" * 64)
        sku.update(variant_hash="b" * 64)
        assert sku.variant_hash == "b" * 64

    def test_update_sets_updated_at(self) -> None:
        """update() advances updated_at."""
        sku = make_sku()
        before = datetime.now(UTC)
        sku.update(sku_code="NEW-CODE")
        after = datetime.now(UTC)
        assert before <= sku.updated_at <= after

    def test_update_no_args_still_sets_updated_at(self) -> None:
        """update() with no args still touches updated_at."""
        sku = make_sku()
        before = datetime.now(UTC)
        sku.update()
        after = datetime.now(UTC)
        assert before <= sku.updated_at <= after

    def test_update_compare_at_price_to_valid_value(self) -> None:
        """update() sets compare_at_price to a Money VO when valid (> price)."""
        sku = make_sku(price=make_money(3000))
        compare = make_money(6000)
        sku.update(compare_at_price=compare)
        assert sku.compare_at_price == compare

    def test_update_compare_at_price_to_none_clears_it(self) -> None:
        """Sentinel: passing None for compare_at_price clears it."""
        price = make_money(3000)
        compare = make_money(6000)
        sku = make_sku(price=price, compare_at_price=compare)
        sku.update(compare_at_price=None)
        assert sku.compare_at_price is None

    def test_update_compare_at_price_omitted_keeps_current(self) -> None:
        """Sentinel: omitting compare_at_price leaves it unchanged."""
        price = make_money(3000)
        compare = make_money(6000)
        sku = make_sku(price=price, compare_at_price=compare)
        sku.update(sku_code="NEW")  # no compare_at_price arg
        assert sku.compare_at_price == compare

    def test_update_compare_at_price_invalid_raises(self) -> None:
        """update() re-validates compare_at_price > price; invalid combo raises."""
        sku = make_sku(price=make_money(5000))
        lower = make_money(3000)
        with pytest.raises(ValueError, match="compare_at_price must be greater than price"):
            sku.update(compare_at_price=lower)

    def test_update_new_price_higher_than_compare_raises(self) -> None:
        """update() re-validates: raising price above compare_at_price raises."""
        price = make_money(3000)
        compare = make_money(6000)
        sku = make_sku(price=price, compare_at_price=compare)
        with pytest.raises(ValueError, match="compare_at_price must be greater than price"):
            sku.update(price=make_money(8000))  # now price > compare_at_price

    def test_update_sku_code_none_keeps_current(self) -> None:
        """update() with sku_code=None leaves sku_code unchanged."""
        sku = make_sku(sku_code="ORIGINAL")
        sku.update(sku_code=None)
        assert sku.sku_code == "ORIGINAL"

    def test_update_price_none_keeps_current(self) -> None:
        """update() with price=None leaves price unchanged."""
        sku = make_sku(price=make_money(1234))
        sku.update(price=None)
        assert sku.price == make_money(1234)


# ---------------------------------------------------------------------------
# Optimistic locking — version field on SKU
# ---------------------------------------------------------------------------


class TestSKUVersionField:
    """Verify version field exists on SKU for optimistic locking."""

    def test_version_field_exists(self) -> None:
        """SKU.version must be present."""
        sku = make_sku()
        assert hasattr(sku, "version")
        assert isinstance(sku.version, int)

    def test_version_starts_at_one(self) -> None:
        """Default version is 1."""
        sku = make_sku()
        assert sku.version == 1
