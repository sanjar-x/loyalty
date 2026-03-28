"""Unit tests for the ProductVariant child entity.

Covers create factory, update (including price/currency interaction),
and soft-delete cascading to SKUs.
"""

import uuid

import pytest

from src.modules.catalog.domain.entities import ProductVariant
from src.modules.catalog.domain.exceptions import MissingRequiredLocalesError
from src.modules.catalog.domain.value_objects import Money
from tests.factories.product_builder import ProductBuilder
from tests.factories.sku_builder import SKUBuilder
from tests.factories.variant_builder import ProductVariantBuilder


def _i18n(en: str, ru: str | None = None) -> dict[str, str]:
    return {"en": en, "ru": ru or en}


# ---------------------------------------------------------------------------
# TestProductVariantCreate
# ---------------------------------------------------------------------------


class TestProductVariantCreate:
    """ProductVariant.create() factory -- happy paths and validation."""

    def test_create_valid(self):
        variant = ProductVariantBuilder().build()
        assert isinstance(variant.id, uuid.UUID)
        assert variant.sort_order == 0

    def test_create_with_name_i18n(self):
        name = _i18n("Red")
        variant = ProductVariantBuilder().with_name_i18n(name).build()
        assert variant.name_i18n == name

    def test_create_rejects_missing_locale(self):
        with pytest.raises(MissingRequiredLocalesError):
            ProductVariant.create(
                product_id=uuid.uuid4(),
                name_i18n={"en": "Red"},
            )

    def test_create_rejects_blank_i18n_values(self):
        with pytest.raises(ValueError):
            ProductVariant.create(
                product_id=uuid.uuid4(),
                name_i18n={"en": "", "ru": "Valid"},
            )

    def test_create_rejects_negative_sort_order(self):
        with pytest.raises(ValueError, match="sort_order must be non-negative"):
            ProductVariant.create(
                product_id=uuid.uuid4(),
                name_i18n=_i18n("V"),
                sort_order=-1,
            )

    def test_create_with_default_price(self):
        variant = (
            ProductVariantBuilder()
            .with_price(Money(amount=1000, currency="RUB"))
            .build()
        )
        assert variant.default_price is not None
        assert variant.default_price.amount == 1000

    def test_create_with_custom_currency(self):
        variant = ProductVariantBuilder().with_currency("USD").build()
        assert variant.default_currency == "USD"

    def test_skus_returns_tuple(self):
        variant = ProductVariantBuilder().build()
        assert isinstance(variant.skus, tuple)


# ---------------------------------------------------------------------------
# TestProductVariantUpdate
# ---------------------------------------------------------------------------


class TestProductVariantUpdate:
    """ProductVariant.update() -- field mutation and validation."""

    def test_update_name_i18n(self):
        variant = ProductVariantBuilder().build()
        new_name = _i18n("Blue")
        variant.update(name_i18n=new_name)
        assert variant.name_i18n == new_name

    def test_update_sort_order(self):
        variant = ProductVariantBuilder().build()
        variant.update(sort_order=5)
        assert variant.sort_order == 5

    def test_update_default_price_and_currency_together(self):
        variant = ProductVariantBuilder().build()
        variant.update(
            default_price=Money(2000, "RUB"),
            default_currency="RUB",
        )
        assert variant.default_price == Money(2000, "RUB")
        assert variant.default_currency == "RUB"

    def test_update_price_only_keeps_currency(self):
        variant = (
            ProductVariantBuilder()
            .with_price(Money(1000, "RUB"))
            .with_currency("RUB")
            .build()
        )
        variant.update(default_price=Money(3000, "RUB"))
        assert variant.default_price == Money(3000, "RUB")
        assert variant.default_currency == "RUB"

    def test_update_description_i18n(self):
        variant = ProductVariantBuilder().build()
        variant.update(description_i18n=_i18n("Desc"))
        assert variant.description_i18n == _i18n("Desc")

    def test_update_rejects_unknown_field(self):
        variant = ProductVariantBuilder().build()
        with pytest.raises(TypeError):
            variant.update(unknown="x")

    def test_update_rejects_blank_name_i18n(self):
        variant = ProductVariantBuilder().build()
        with pytest.raises(ValueError):
            variant.update(name_i18n={"en": "", "ru": "Valid"})

    def test_update_rejects_negative_sort_order(self):
        variant = ProductVariantBuilder().build()
        with pytest.raises(ValueError):
            variant.update(sort_order=-1)


# ---------------------------------------------------------------------------
# TestProductVariantSoftDelete
# ---------------------------------------------------------------------------


class TestProductVariantSoftDelete:
    """ProductVariant.soft_delete() -- cascading and idempotency."""

    def test_soft_delete_sets_deleted_at(self):
        variant = ProductVariantBuilder().build()
        variant.soft_delete()
        assert variant.deleted_at is not None

    def test_soft_delete_cascades_to_skus(self):
        product = ProductBuilder().build()
        variant_id = product.variants[0].id
        sku = product.add_sku(
            variant_id, sku_code="SKU-CASCADE", price=Money(500, "RUB")
        )
        # Soft-delete the variant directly
        product.variants[0].soft_delete()
        assert sku.deleted_at is not None

    def test_soft_delete_idempotent(self):
        variant = ProductVariantBuilder().build()
        variant.soft_delete()
        first_deleted_at = variant.deleted_at
        variant.soft_delete()
        assert variant.deleted_at == first_deleted_at
