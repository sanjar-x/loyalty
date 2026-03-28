"""Unit tests for the SKU child entity.

Covers construction validation (__attrs_post_init__), update with
cross-field price/compare_at_price validation, and soft-delete.
"""

import uuid

import pytest

from src.modules.catalog.domain.value_objects import Money
from tests.factories.product_builder import ProductBuilder
from tests.factories.sku_builder import SKUBuilder


# ---------------------------------------------------------------------------
# TestSKUConstruction
# ---------------------------------------------------------------------------


class TestSKUConstruction:
    """SKU created via Product.add_sku() -- validation guards."""

    def test_create_via_product_add_sku(self):
        sku = SKUBuilder().build()
        assert isinstance(sku.id, uuid.UUID)
        assert sku.sku_code.startswith("SKU-")

    def test_create_with_price(self):
        sku = SKUBuilder().with_price(Money(1000, "RUB")).build()
        assert sku.price is not None
        assert sku.price.amount == 1000

    def test_create_with_valid_compare_at_price(self):
        sku = (
            SKUBuilder()
            .with_price(Money(1000, "RUB"))
            .with_compare_at_price(Money(2000, "RUB"))
            .build()
        )
        assert sku.compare_at_price is not None
        assert sku.compare_at_price.amount == 2000

    def test_rejects_compare_at_without_price(self):
        product = ProductBuilder().build()
        variant_id = product.variants[0].id
        with pytest.raises(ValueError, match="compare_at_price cannot be set when price is None"):
            product.add_sku(
                variant_id,
                sku_code="SKU-NOPR",
                price=None,
                compare_at_price=Money(2000, "RUB"),
            )

    def test_rejects_compare_at_less_than_price(self):
        product = ProductBuilder().build()
        variant_id = product.variants[0].id
        with pytest.raises(ValueError, match="compare_at_price must be greater than price"):
            product.add_sku(
                variant_id,
                sku_code="SKU-LOW",
                price=Money(2000, "RUB"),
                compare_at_price=Money(1000, "RUB"),
            )

    def test_rejects_compare_at_equal_to_price(self):
        product = ProductBuilder().build()
        variant_id = product.variants[0].id
        with pytest.raises(ValueError, match="compare_at_price must be greater than price"):
            product.add_sku(
                variant_id,
                sku_code="SKU-EQ",
                price=Money(1000, "RUB"),
                compare_at_price=Money(1000, "RUB"),
            )

    def test_rejects_compare_at_currency_mismatch(self):
        product = ProductBuilder().build()
        variant_id = product.variants[0].id
        with pytest.raises(ValueError, match="must match price currency"):
            product.add_sku(
                variant_id,
                sku_code="SKU-CUR",
                price=Money(1000, "RUB"),
                compare_at_price=Money(2000, "USD"),
            )

    def test_create_inactive(self):
        sku = SKUBuilder().as_inactive().build()
        assert sku.is_active is False


# ---------------------------------------------------------------------------
# TestSKUUpdate
# ---------------------------------------------------------------------------


class TestSKUUpdate:
    """SKU.update() -- field mutation with cross-field validation."""

    def test_update_sku_code(self):
        sku = SKUBuilder().build()
        sku.update(sku_code="NEW-CODE")
        assert sku.sku_code == "NEW-CODE"

    def test_update_price(self):
        sku = SKUBuilder().with_price(Money(1000, "RUB")).build()
        sku.update(price=Money(5000, "RUB"))
        assert sku.price == Money(5000, "RUB")

    def test_update_is_active(self):
        sku = SKUBuilder().build()
        sku.update(is_active=False)
        assert sku.is_active is False

    def test_update_rejects_unknown_field(self):
        sku = SKUBuilder().build()
        with pytest.raises(TypeError):
            sku.update(unknown="x")

    def test_update_compare_at_price(self):
        sku = SKUBuilder().with_price(Money(1000, "RUB")).build()
        sku.update(compare_at_price=Money(3000, "RUB"))
        assert sku.compare_at_price == Money(3000, "RUB")

    def test_update_price_revalidates_compare_at(self):
        """Updating price to exceed existing compare_at_price should raise."""
        sku = (
            SKUBuilder()
            .with_price(Money(1000, "RUB"))
            .with_compare_at_price(Money(2000, "RUB"))
            .build()
        )
        with pytest.raises(ValueError, match="compare_at_price must be greater than price"):
            sku.update(price=Money(3000, "RUB"))


# ---------------------------------------------------------------------------
# TestSKUSoftDelete
# ---------------------------------------------------------------------------


class TestSKUSoftDelete:
    """SKU.soft_delete() -- sets timestamp, idempotent."""

    def test_soft_delete_sets_deleted_at(self):
        sku = SKUBuilder().build()
        sku.soft_delete()
        assert sku.deleted_at is not None

    def test_soft_delete_idempotent(self):
        sku = SKUBuilder().build()
        sku.soft_delete()
        first_deleted_at = sku.deleted_at
        sku.soft_delete()
        assert sku.deleted_at == first_deleted_at
